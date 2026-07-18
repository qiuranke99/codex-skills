#!/usr/bin/env python3
"""Validate that every top-level Skill package works as an isolated package.

The validator intentionally uses only the Python standard library and never
imports or executes anything from ``high-control-ai-tvc``.  Each directory
directly below the repository root that contains ``SKILL.md`` is treated as a
published Skill package.

Exit codes are stable:

* 0: every discovered package passed;
* 1: validation completed and found contract violations;
* 2: command-line or validator configuration error;
* 3: unexpected validator failure.

Validation issue codes are also stable and are emitted in the JSON report.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Iterable, Mapping, Sequence


SCHEMA_VERSION = 1
EXIT_OK = 0
EXIT_VALIDATION_FAILED = 1
EXIT_CONFIGURATION_ERROR = 2
EXIT_INTERNAL_ERROR = 3

# Stable report issue codes.  Keep values backward compatible once consumed by
# CI; callers should key on these values rather than human-readable messages.
E_PACKAGE_COUNT_MISMATCH = "E_PACKAGE_COUNT_MISMATCH"
E_NO_SKILL_PACKAGES = "E_NO_SKILL_PACKAGES"
E_SKILL_MD_UNREADABLE = "E_SKILL_MD_UNREADABLE"
E_AGENT_METADATA_MISSING = "E_AGENT_METADATA_MISSING"
E_AGENT_METADATA_INVALID = "E_AGENT_METADATA_INVALID"
E_FORBIDDEN_RELEASE_GATE = "E_FORBIDDEN_RELEASE_GATE"
E_CROSS_PACKAGE_PATH = "E_CROSS_PACKAGE_PATH"
E_SIBLING_IMPORT = "E_SIBLING_IMPORT"
E_REPO_ROOT_PATH = "E_REPO_ROOT_PATH"
E_DECLARED_SCRIPT_MISSING = "E_DECLARED_SCRIPT_MISSING"
E_EXTERNAL_LINK = "E_EXTERNAL_LINK"
E_ISOLATION_COPY_FAILED = "E_ISOLATION_COPY_FAILED"
E_PYTHON_COMPILE_FAILED = "E_PYTHON_COMPILE_FAILED"
E_TEST_CONFIG_INVALID = "E_TEST_CONFIG_INVALID"
E_TEST_COMMAND_UNSAFE = "E_TEST_COMMAND_UNSAFE"
E_TEST_COMMAND_FAILED = "E_TEST_COMMAND_FAILED"
E_TEST_COMMAND_TIMEOUT = "E_TEST_COMMAND_TIMEOUT"

SAFETY_BLOCKING_CODES = {
    E_FORBIDDEN_RELEASE_GATE,
    E_CROSS_PACKAGE_PATH,
    E_SIBLING_IMPORT,
    E_REPO_ROOT_PATH,
    E_EXTERNAL_LINK,
    E_TEST_CONFIG_INVALID,
    E_TEST_COMMAND_UNSAFE,
}

FORBIDDEN_SKILL_MARKERS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "HIGH_CONTROL_RELEASE_GATE",
        re.compile(r"\bHIGH_CONTROL_RELEASE_GATE(?:_V\d+)?\b", re.IGNORECASE),
    ),
    (
        "release-control",
        re.compile(r"\brelease[-_]control(?:\.(?:ps1|sh|py))?\b", re.IGNORECASE),
    ),
    ("SUITE_MANIFEST", re.compile(r"\bSUITE_MANIFEST(?:\.json)?\b", re.IGNORECASE)),
    ("ready_latest", re.compile(r"\bready_latest\b", re.IGNORECASE)),
    (
        "mandatory suite receipt",
        re.compile(r"\bmandatory(?:[\s_-]+)suite(?:[\s_-]+)receipt\b", re.IGNORECASE),
    ),
)

SCRIPT_REFERENCE_RE = re.compile(
    r"(?P<path>(?:\.\.?[\\/])?(?:[A-Za-z0-9_.-]+[\\/])+[A-Za-z0-9_.-]+\.(?:py|ps1|sh))",
    re.IGNORECASE,
)
WINDOWS_ABSOLUTE_RE = re.compile(r"(?<![A-Za-z0-9_])(?:[A-Za-z]:[\\/]|\\\\)[^\s`\"'<>]+")
PARENT_PATH_RE = re.compile(r"(?<![A-Za-z0-9_.])(?:\.\.[\\/])+")
PATH_TARGET_NAME_RE = re.compile(r"(?:PATH|ROOT|DIR|DIRECTORY|HOME|FILE|SCRIPT|SHARED)$", re.IGNORECASE)

PACKAGE_CONFIG_NAMES = ("standalone-validation.json", ".standalone-validation.json")
MAX_CAPTURE_CHARS = 12_000
MAX_COMMAND_ARGS = 64
MAX_COMMAND_ARG_CHARS = 4_096


@dataclass(frozen=True)
class Issue:
    code: str
    message: str
    path: str | None = None
    line: int | None = None
    evidence: str | None = None
    details: Mapping[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.path is not None:
            result["path"] = self.path
        if self.line is not None:
            result["line"] = self.line
        if self.evidence is not None:
            result["evidence"] = self.evidence
        if self.details is not None:
            result["details"] = dict(self.details)
        return result


@dataclass
class PackageResult:
    name: str
    path: str
    issues: list[Issue] = field(default_factory=list)
    checks: dict[str, Any] = field(default_factory=dict)
    declared_scripts: list[str] = field(default_factory=list)
    _issue_keys: set[tuple[Any, ...]] = field(default_factory=set, repr=False)

    def add_issue(self, issue: Issue) -> None:
        key = (issue.code, issue.path, issue.line, issue.evidence, issue.message)
        if key not in self._issue_keys:
            self._issue_keys.add(key)
            self.issues.append(issue)

    def as_dict(self) -> dict[str, Any]:
        ordered_issues = sorted(
            self.issues,
            key=lambda issue: (
                issue.path or "",
                issue.line if issue.line is not None else -1,
                issue.code,
                issue.message,
            ),
        )
        return {
            "name": self.name,
            "path": self.path,
            "status": "pass" if not ordered_issues else "fail",
            "checks": self.checks,
            "declared_scripts": sorted(set(self.declared_scripts)),
            "issues": [issue.as_dict() for issue in ordered_issues],
        }


class ConfigurationError(ValueError):
    """A caller-controlled validator configuration is invalid."""


class UnsafeCommandError(ConfigurationError):
    """A declared command is syntactically valid but unsafe to execute."""


def _display_path(path: Path, repo_root: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except (OSError, ValueError):
        return str(path)


def _line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _line_evidence(text: str, line_number: int) -> str:
    lines = text.splitlines()
    if not 1 <= line_number <= len(lines):
        return ""
    value = " ".join(lines[line_number - 1].strip().split())
    return value[:240]


def _truncate(value: str | None) -> str:
    if not value:
        return ""
    value = value.replace("\x00", "")
    if len(value) <= MAX_CAPTURE_CHARS:
        return value
    return value[:MAX_CAPTURE_CHARS] + "\n...<truncated>"


def discover_skill_packages(repo_root: Path) -> list[Path]:
    """Return sorted top-level directories that contain ``SKILL.md``."""

    try:
        children = list(repo_root.iterdir())
    except OSError as exc:
        raise ConfigurationError(f"cannot enumerate repository root: {exc}") from exc
    return sorted(
        (
            child
            for child in children
            if child.is_dir() and not child.name.startswith(".") and (child / "SKILL.md").is_file()
        ),
        key=lambda value: value.name.casefold(),
    )


def _read_utf8(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def _scan_forbidden_markers(
    skill_path: Path,
    text: str,
    result: PackageResult,
    repo_root: Path,
) -> None:
    found: list[str] = []
    for marker_name, pattern in FORBIDDEN_SKILL_MARKERS:
        match = pattern.search(text)
        if match is None:
            continue
        found.append(marker_name)
        line = _line_number(text, match.start())
        result.add_issue(
            Issue(
                E_FORBIDDEN_RELEASE_GATE,
                f"SKILL.md contains forbidden High-Control release coupling: {marker_name}",
                _display_path(skill_path, repo_root),
                line,
                _line_evidence(text, line),
                {"marker": marker_name},
            )
        )
    result.checks["forbidden_release_gate"] = {
        "status": "fail" if found else "pass",
        "markers": found,
    }


def _looks_absolute_path(value: str) -> bool:
    if "://" in value:
        return False
    return PureWindowsPath(value).is_absolute() or PurePosixPath(value).is_absolute()


def _path_mentions_package(value: str, package_name: str) -> bool:
    normalized = value.replace("\\", "/")
    escaped = re.escape(package_name)
    return bool(
        re.search(rf"(?:^|\.\./|/)\s*[\"'`]?{escaped}(?:/|[\"'`\s)]|$)", normalized, re.IGNORECASE)
        or re.search(rf"/\s*[\"']{escaped}[\"']", normalized, re.IGNORECASE)
        or re.search(rf"\bJoin-Path\b[^\r\n]*[\"']?{escaped}(?:[\\/\"']|$)", value, re.IGNORECASE)
    )


def _scan_text_cross_package_paths(
    path: Path,
    text: str,
    package_name: str,
    all_package_names: Sequence[str],
    result: PackageResult,
    repo_root: Path,
) -> None:
    display = _display_path(path, repo_root)
    lines = text.splitlines()
    for other_name in all_package_names:
        if other_name == package_name:
            continue
        for index, line_text in enumerate(lines, start=1):
            if _path_mentions_package(line_text, other_name):
                result.add_issue(
                    Issue(
                        E_CROSS_PACKAGE_PATH,
                        f"reference escapes the package and targets sibling package {other_name!r}",
                        display,
                        index,
                        " ".join(line_text.strip().split())[:240],
                        {"target_package": other_name},
                    )
                )
                break

    root_forms = {
        str(repo_root),
        str(repo_root).replace("\\", "/"),
        str(repo_root).replace("\\", "\\\\"),
    }
    root_forms.discard("")
    for index, line_text in enumerate(lines, start=1):
        if any(root_form.casefold() in line_text.casefold() for root_form in root_forms):
            result.add_issue(
                Issue(
                    E_REPO_ROOT_PATH,
                    "hard-coded repository-root path prevents isolated installation",
                    display,
                    index,
                    " ".join(line_text.strip().split())[:240],
                )
            )
            break


def _scan_skill_parent_and_absolute_paths(
    skill_path: Path,
    text: str,
    result: PackageResult,
    repo_root: Path,
) -> None:
    display = _display_path(skill_path, repo_root)
    for index, line_text in enumerate(text.splitlines(), start=1):
        parent_match = PARENT_PATH_RE.search(line_text)
        if parent_match is not None:
            result.add_issue(
                Issue(
                    E_REPO_ROOT_PATH,
                    "SKILL.md declares a parent-relative path outside its package",
                    display,
                    index,
                    " ".join(line_text.strip().split())[:240],
                )
            )
        absolute_match = WINDOWS_ABSOLUTE_RE.search(line_text)
        if absolute_match is not None:
            result.add_issue(
                Issue(
                    E_REPO_ROOT_PATH,
                    "SKILL.md contains a hard-coded absolute filesystem path",
                    display,
                    index,
                    absolute_match.group(0)[:240],
                )
            )


def _assignment_names(node: ast.AST) -> list[str]:
    targets: list[ast.AST] = []
    if isinstance(node, (ast.Assign, ast.AnnAssign, ast.NamedExpr)):
        if isinstance(node, ast.Assign):
            targets.extend(node.targets)
        else:
            targets.append(node.target)
    names: list[str] = []
    for target in targets:
        if isinstance(target, ast.Name):
            names.append(target.id)
    return names


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = _call_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    return ""


def _constant_string(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _path_up_moves(
    node: ast.AST,
    assignments: Mapping[str, ast.AST],
    seen: frozenset[str] = frozenset(),
) -> int | None:
    """Estimate parent moves from ``__file__`` for a pathlib-style expression."""

    if isinstance(node, ast.Name):
        if node.id == "__file__":
            return 0
        if node.id in assignments and node.id not in seen:
            return _path_up_moves(assignments[node.id], assignments, seen | {node.id})
        return None
    if isinstance(node, ast.Call):
        name = _call_name(node.func).casefold()
        if name in {"resolve", "absolute", "expanduser"} or name.endswith(
            (".resolve", ".absolute", ".expanduser")
        ):
            return _path_up_moves(node.func.value, assignments, seen)  # type: ignore[attr-defined]
        if name in {"path", "pathlib.path", "os.fspath"} and node.args:
            return _path_up_moves(node.args[0], assignments, seen)
        if name.endswith("os.path.dirname") or name == "dirname":
            if node.args:
                base = _path_up_moves(node.args[0], assignments, seen)
                return None if base is None else base + 1
        return None
    if isinstance(node, ast.Attribute) and node.attr == "parent":
        base = _path_up_moves(node.value, assignments, seen)
        return None if base is None else base + 1
    if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Attribute) and node.value.attr == "parents":
        base = _path_up_moves(node.value.value, assignments, seen)
        index: int | None = None
        if isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, int):
            index = node.slice.value
        if base is None or index is None or index < 0:
            return None
        return base + index + 1
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        base = _path_up_moves(node.left, assignments, seen)
        if base is None:
            return None
        part = _constant_string(node.right)
        if part is None:
            return base
        parent_count = 0
        for component in part.replace("\\", "/").split("/"):
            if component == "..":
                parent_count += 1
            elif component not in {"", "."}:
                break
        return base + parent_count
    return None


def _path_context(parent: ast.AST | None, grandparent: ast.AST | None) -> bool:
    if isinstance(parent, ast.BinOp) and isinstance(parent.op, ast.Div):
        return True
    if isinstance(parent, ast.Call):
        name = _call_name(parent.func).casefold()
        return name in {
            "path",
            "pathlib.path",
            "open",
            "io.open",
            "os.open",
            "os.chdir",
            "os.listdir",
            "os.scandir",
            "os.stat",
            "os.unlink",
            "os.remove",
            "os.makedirs",
            "shutil.copy",
            "shutil.copy2",
            "shutil.copytree",
            "shutil.move",
            "subprocess.run",
            "subprocess.call",
            "subprocess.check_call",
            "subprocess.check_output",
            "importlib.util.spec_from_file_location",
        }
    if isinstance(parent, (ast.List, ast.Tuple)) and isinstance(grandparent, ast.Call):
        return _path_context(grandparent, None)
    if isinstance(parent, (ast.Assign, ast.AnnAssign, ast.NamedExpr)):
        return any(PATH_TARGET_NAME_RE.search(name) for name in _assignment_names(parent))
    return False


def _is_parent_escape_operation(node: ast.AST) -> bool:
    """Return whether *node* itself performs a parent-walking operation.

    A name that merely reuses an already-invalid path is deliberately not an
    origin.  Reporting only origins keeps one actionable finding at the path
    definition instead of repeating it at every downstream read.
    """

    if isinstance(node, ast.Subscript):
        return isinstance(node.value, ast.Attribute) and node.value.attr == "parents"
    if isinstance(node, ast.Attribute):
        return node.attr == "parent"
    if isinstance(node, ast.Call):
        name = _call_name(node.func).casefold()
        return name == "dirname" or name.endswith("os.path.dirname")
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        value = _constant_string(node.right)
        if value is None:
            return False
        return ".." in PurePosixPath(value.replace("\\", "/")).parts
    return False


def _scan_python_dependencies(
    path: Path,
    text: str,
    package_root: Path,
    package_name: str,
    all_package_names: Sequence[str],
    result: PackageResult,
    repo_root: Path,
) -> None:
    display = _display_path(path, repo_root)
    try:
        tree = ast.parse(text, filename=display)
    except SyntaxError:
        # The isolated compiler emits the canonical syntax failure.
        return

    import_variants: dict[str, str] = {}
    for other_name in all_package_names:
        if other_name == package_name:
            continue
        import_variants[other_name.casefold()] = other_name
        import_variants[other_name.replace("-", "_").casefold()] = other_name

    assignments: dict[str, ast.AST] = {}
    parent_map: dict[ast.AST, ast.AST] = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parent_map[child] = parent
        if isinstance(parent, ast.Assign):
            for target in parent.targets:
                if isinstance(target, ast.Name):
                    assignments[target.id] = parent.value
        elif isinstance(parent, ast.AnnAssign) and isinstance(parent.target, ast.Name) and parent.value is not None:
            assignments[parent.target.id] = parent.value

    for node in ast.walk(tree):
        imported_name: str | None = None
        if isinstance(node, ast.Import):
            for alias in node.names:
                root_name = alias.name.split(".", 1)[0].casefold()
                if root_name in import_variants:
                    imported_name = import_variants[root_name]
                    break
        elif isinstance(node, ast.ImportFrom):
            if node.level >= 2:
                result.add_issue(
                    Issue(
                        E_REPO_ROOT_PATH,
                        "relative Python import traverses beyond the package-local module boundary",
                        display,
                        getattr(node, "lineno", None),
                        _line_evidence(text, getattr(node, "lineno", 0)),
                    )
                )
            if node.module:
                root_name = node.module.split(".", 1)[0].casefold()
                if root_name in import_variants:
                    imported_name = import_variants[root_name]
        if imported_name is not None:
            result.add_issue(
                Issue(
                    E_SIBLING_IMPORT,
                    f"Python import depends on sibling package {imported_name!r}",
                    display,
                    getattr(node, "lineno", None),
                    _line_evidence(text, getattr(node, "lineno", 0)),
                    {"target_package": imported_name},
                )
            )

    relative_path = path.relative_to(package_root)
    max_file_parent_moves_inside_package = len(relative_path.parent.parts) + 1
    for node in ast.walk(tree):
        moves = _path_up_moves(node, assignments)
        if (
            moves is not None
            and moves > max_file_parent_moves_inside_package
            and _is_parent_escape_operation(node)
        ):
            line = getattr(node, "lineno", None)
            result.add_issue(
                Issue(
                    E_REPO_ROOT_PATH,
                    "Python path calculation walks above the Skill package root",
                    display,
                    line,
                    _line_evidence(text, line or 0),
                    {
                        "parent_moves": moves,
                        "maximum_package_local_parent_moves": max_file_parent_moves_inside_package,
                    },
                )
            )

        value = _constant_string(node)
        if value is None:
            continue
        parent = parent_map.get(node)
        grandparent = parent_map.get(parent) if parent is not None else None
        if not _path_context(parent, grandparent):
            continue
        line = getattr(node, "lineno", None)
        if _looks_absolute_path(value):
            result.add_issue(
                Issue(
                    E_REPO_ROOT_PATH,
                    "Python code uses a hard-coded absolute filesystem path",
                    display,
                    line,
                    _line_evidence(text, line or 0),
                )
            )
        normalized_parts = value.replace("\\", "/").split("/")
        if normalized_parts and normalized_parts[0] == "..":
            result.add_issue(
                Issue(
                    E_REPO_ROOT_PATH,
                    "Python path operation uses a parent-relative path outside isolated cwd",
                    display,
                    line,
                    _line_evidence(text, line or 0),
                )
            )


def _scan_shell_dependencies(
    path: Path,
    text: str,
    result: PackageResult,
    repo_root: Path,
) -> None:
    display = _display_path(path, repo_root)
    for index, line_text in enumerate(text.splitlines(), start=1):
        if PARENT_PATH_RE.search(line_text):
            result.add_issue(
                Issue(
                    E_REPO_ROOT_PATH,
                    "shell path traverses above the isolated package cwd",
                    display,
                    index,
                    " ".join(line_text.strip().split())[:240],
                )
            )
        if WINDOWS_ABSOLUTE_RE.search(line_text):
            result.add_issue(
                Issue(
                    E_REPO_ROOT_PATH,
                    "shell code contains a hard-coded absolute filesystem path",
                    display,
                    index,
                    " ".join(line_text.strip().split())[:240],
                )
            )


def _extract_declared_scripts(
    skill_path: Path,
    text: str,
    package_root: Path,
    result: PackageResult,
    repo_root: Path,
) -> None:
    display = _display_path(skill_path, repo_root)
    references: set[str] = set()
    for match in SCRIPT_REFERENCE_RE.finditer(text):
        raw = match.group("path").replace("\\", "/")
        if raw.startswith("../") or raw.startswith("./../"):
            continue
        normalized = raw[2:] if raw.startswith("./") else raw
        try:
            relative = Path(normalized)
        except (TypeError, ValueError):
            continue
        if relative.is_absolute() or ".." in relative.parts:
            continue
        references.add(relative.as_posix())
        candidate = package_root / relative
        if not candidate.is_file():
            line = _line_number(text, match.start())
            result.add_issue(
                Issue(
                    E_DECLARED_SCRIPT_MISSING,
                    f"SKILL.md declares missing package-local script {relative.as_posix()!r}",
                    display,
                    line,
                    _line_evidence(text, line),
                    {"script": relative.as_posix()},
                )
            )
    result.declared_scripts.extend(sorted(references))
    missing = [issue for issue in result.issues if issue.code == E_DECLARED_SCRIPT_MISSING]
    result.checks["declared_scripts"] = {
        "status": "fail" if missing else "pass",
        "count": len(references),
    }


def _validate_agent_metadata(package_root: Path, result: PackageResult, repo_root: Path) -> None:
    metadata_path = package_root / "agents" / "openai.yaml"
    display = _display_path(metadata_path, repo_root)
    if not metadata_path.is_file():
        result.add_issue(
            Issue(
                E_AGENT_METADATA_MISSING,
                "required agents/openai.yaml metadata is missing",
                display,
            )
        )
        result.checks["agent_metadata"] = {"status": "fail", "path": "agents/openai.yaml"}
        return
    try:
        text = _read_utf8(metadata_path)
    except (OSError, UnicodeError) as exc:
        result.add_issue(
            Issue(E_AGENT_METADATA_INVALID, f"cannot read agents/openai.yaml as UTF-8: {exc}", display)
        )
        result.checks["agent_metadata"] = {"status": "fail", "path": "agents/openai.yaml"}
        return
    required_patterns = {
        "interface": re.compile(r"(?m)^interface\s*:\s*(?:#.*)?$"),
        "display_name": re.compile(r"(?m)^\s+display_name\s*:\s*\S+"),
        "short_description": re.compile(r"(?m)^\s+short_description\s*:\s*\S+"),
    }
    missing_fields = [name for name, pattern in required_patterns.items() if pattern.search(text) is None]
    if missing_fields:
        result.add_issue(
            Issue(
                E_AGENT_METADATA_INVALID,
                "agents/openai.yaml is missing required metadata fields",
                display,
                details={"missing_fields": missing_fields},
            )
        )
    result.checks["agent_metadata"] = {
        "status": "fail" if missing_fields else "pass",
        "path": "agents/openai.yaml",
        "missing_fields": missing_fields,
    }


def _scan_external_links(package_root: Path, result: PackageResult, repo_root: Path) -> bool:
    found = False
    for current_root, directory_names, file_names in os.walk(package_root, followlinks=False):
        current = Path(current_root)
        for name in sorted(directory_names + file_names):
            candidate = current / name
            is_junction = getattr(candidate, "is_junction", lambda: False)()
            if candidate.is_symlink() or is_junction:
                found = True
                result.add_issue(
                    Issue(
                        E_EXTERNAL_LINK,
                        "symbolic links/junctions are not allowed inside standalone packages",
                        _display_path(candidate, repo_root),
                    )
                )
    result.checks["external_links"] = {"status": "fail" if found else "pass"}
    return found


def _source_files(package_root: Path) -> list[Path]:
    allowed_suffixes = {".py", ".ps1", ".sh"}
    ignored_parts = {".git", ".venv", "venv", "__pycache__", "node_modules"}
    return sorted(
        (
            path
            for path in package_root.rglob("*")
            if path.is_file()
            and path.suffix.casefold() in allowed_suffixes
            and not ignored_parts.intersection(path.relative_to(package_root).parts)
        ),
        key=lambda value: value.relative_to(package_root).as_posix().casefold(),
    )


def _load_json(path: Path) -> Any:
    try:
        return json.loads(_read_utf8(path))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ConfigurationError(f"cannot read JSON configuration {path}: {exc}") from exc


def _load_root_test_config(config_path: Path | None, repo_root: Path) -> dict[str, Any]:
    if config_path is None:
        return {}
    path = config_path if config_path.is_absolute() else repo_root / config_path
    payload = _load_json(path)
    if not isinstance(payload, dict):
        raise ConfigurationError("root test configuration must be a JSON object")
    packages = payload.get("packages", payload)
    if not isinstance(packages, dict):
        raise ConfigurationError("root test configuration 'packages' must be a JSON object")
    return dict(packages)


def _package_test_declaration(
    package_root: Path,
    package_name: str,
    root_config: Mapping[str, Any],
) -> tuple[dict[str, Any] | None, str | None]:
    if package_name in root_config:
        value = root_config[package_name]
        if not isinstance(value, dict):
            raise ConfigurationError(f"test configuration for {package_name!r} must be a JSON object")
        return dict(value), "root_config"

    config_paths = [package_root / name for name in PACKAGE_CONFIG_NAMES if (package_root / name).exists()]
    if len(config_paths) > 1:
        raise ConfigurationError(
            f"package {package_name!r} contains multiple standalone test configuration files"
        )
    if not config_paths:
        return None, None
    payload = _load_json(config_paths[0])
    if not isinstance(payload, dict):
        raise ConfigurationError(f"{config_paths[0].name} must contain a JSON object")
    return dict(payload), config_paths[0].name


def _normalise_test_declaration(
    declaration: Mapping[str, Any],
    maximum_timeout: float,
) -> tuple[list[str], float]:
    test_value: Any = declaration.get("deterministic_test", declaration)
    if isinstance(test_value, dict):
        command = test_value.get("command", test_value.get("test_command"))
        timeout_value = test_value.get("timeout_seconds", declaration.get("timeout_seconds", maximum_timeout))
    else:
        command = declaration.get("test_command")
        timeout_value = declaration.get("timeout_seconds", maximum_timeout)
    if not isinstance(command, list) or not command or not all(isinstance(item, str) and item for item in command):
        raise ConfigurationError("deterministic test command must be a non-empty JSON array of strings")
    if len(command) > MAX_COMMAND_ARGS or any(len(item) > MAX_COMMAND_ARG_CHARS for item in command):
        raise ConfigurationError("deterministic test command exceeds the safety size limit")
    if isinstance(timeout_value, bool) or not isinstance(timeout_value, (int, float)):
        raise ConfigurationError("timeout_seconds must be numeric")
    timeout_seconds = float(timeout_value)
    if not 0 < timeout_seconds <= maximum_timeout:
        raise ConfigurationError(
            f"timeout_seconds must be greater than zero and no more than {maximum_timeout:g}"
        )
    return list(command), timeout_seconds


def _contains_parent_or_absolute_argument(argument: str) -> bool:
    if _looks_absolute_path(argument):
        return True
    normalized = argument.replace("\\", "/")
    return ".." in PurePosixPath(normalized).parts or normalized.startswith("~")


def _prepare_safe_command(command: Sequence[str], isolated_package: Path) -> list[str]:
    raw = list(command)
    executable = raw[0]
    executable_name = Path(executable).name.casefold()
    python_names = {"{python}", "python", "python.exe", "python3", "python3.exe", "py", "py.exe"}
    shell_names = {"pwsh", "pwsh.exe", "powershell", "powershell.exe", "bash", "bash.exe", "sh", "sh.exe"}
    if executable.casefold() in python_names or executable_name in python_names:
        # -E/-s isolate environment and user-site configuration while keeping
        # the package-local script directory importable.  Full -I would remove
        # that directory and incorrectly break ordinary local test imports.
        prepared = [sys.executable, "-E", "-s", "-B", *raw[1:]]
        if any(argument in {"-c", "--command"} for argument in raw[1:]):
            raise UnsafeCommandError("inline Python commands are not allowed; declare a package-local test script")
        script_candidates = [argument for argument in raw[1:] if argument.casefold().endswith(".py")]
    elif executable_name in shell_names:
        resolved = shutil.which(executable)
        if resolved is None:
            raise ConfigurationError(f"declared test interpreter {executable!r} is not available")
        prepared = [resolved, *raw[1:]]
        forbidden_flags = {"-command", "-encodedcommand", "-c"}
        if any(argument.casefold() in forbidden_flags for argument in raw[1:]):
            raise UnsafeCommandError("inline shell commands are not allowed; declare a package-local test script")
        script_candidates = [
            argument
            for argument in raw[1:]
            if argument.casefold().endswith((".ps1", ".sh"))
        ]
    else:
        raise UnsafeCommandError(
            "test command executable must be {python}, python, python3, py, pwsh, powershell, bash, or sh"
        )

    shell_operators = {"|", "||", "&", "&&", ";", ">", ">>", "<", "<<"}
    for argument in raw[1:]:
        if argument in shell_operators:
            raise UnsafeCommandError("shell operators are not allowed in deterministic test commands")
        if argument.startswith("-"):
            continue
        if ("/" in argument or "\\" in argument or argument.casefold().endswith((".py", ".ps1", ".sh"))) and _contains_parent_or_absolute_argument(argument):
            raise UnsafeCommandError(f"test command argument escapes the isolated package: {argument!r}")
    for script in script_candidates:
        candidate = isolated_package / Path(script.replace("\\", "/"))
        try:
            candidate.resolve().relative_to(isolated_package.resolve())
        except (OSError, ValueError) as exc:
            raise UnsafeCommandError(f"test script escapes isolated package: {script!r}") from exc
        if not candidate.is_file():
            raise ConfigurationError(f"declared deterministic test script does not exist: {script!r}")
    return prepared


def _isolated_environment(home: Path) -> dict[str, str]:
    temporary = home / "tmp"
    temporary.mkdir(parents=True, exist_ok=True)
    environment: dict[str, str] = {}
    for key in ("SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT", "LANG", "LC_ALL", "TZ"):
        value = os.environ.get(key)
        if value:
            environment[key] = value
    executable_dir = str(Path(sys.executable).resolve().parent)
    system32 = str(Path(os.environ.get("SYSTEMROOT", r"C:\Windows")) / "System32")
    environment["PATH"] = os.pathsep.join((executable_dir, system32))
    environment.update(
        {
            "HOME": str(home),
            "USERPROFILE": str(home),
            "APPDATA": str(home / "AppData" / "Roaming"),
            "LOCALAPPDATA": str(home / "AppData" / "Local"),
            "XDG_CACHE_HOME": str(home / ".cache"),
            "XDG_CONFIG_HOME": str(home / ".config"),
            "XDG_DATA_HOME": str(home / ".local" / "share"),
            "TEMP": str(temporary),
            "TMP": str(temporary),
            "TMPDIR": str(temporary),
            "PYTHONPATH": "",
            "PYTHONNOUSERSITE": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONUTF8": "1",
            "PIP_DISABLE_PIP_VERSION_CHECK": "1",
            "NO_COLOR": "1",
        }
    )
    return environment


PYTHON_COMPILE_PROGRAM = r"""
from pathlib import Path
import json
import sys

ignored = {'.git', '.venv', 'venv', '__pycache__', 'node_modules'}
files = sorted(
    path for path in Path('.').rglob('*.py')
    if not ignored.intersection(path.parts)
)
failures = []
for path in files:
    try:
        source = path.read_bytes()
        compile(source, path.as_posix(), 'exec', dont_inherit=True)
    except Exception as exc:
        failures.append({
            'path': path.as_posix(),
            'type': type(exc).__name__,
            'message': str(exc),
        })
print(json.dumps({'python_files': len(files), 'failures': failures}, sort_keys=True))
raise SystemExit(1 if failures else 0)
""".strip()


def _run_python_compile(
    isolated_package: Path,
    environment: Mapping[str, str],
    timeout_seconds: float,
) -> tuple[bool, dict[str, Any]]:
    command = [sys.executable, "-I", "-S", "-B", "-c", PYTHON_COMPILE_PROGRAM]
    try:
        completed = subprocess.run(
            command,
            cwd=isolated_package,
            env=dict(environment),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return False, {
            "status": "timeout",
            "timeout_seconds": timeout_seconds,
            "stdout": _truncate(exc.stdout if isinstance(exc.stdout, str) else ""),
            "stderr": _truncate(exc.stderr if isinstance(exc.stderr, str) else ""),
        }
    payload: dict[str, Any] = {}
    try:
        parsed = json.loads(completed.stdout.strip())
        if isinstance(parsed, dict):
            payload = parsed
    except json.JSONDecodeError:
        payload = {}
    payload.update(
        {
            "status": "pass" if completed.returncode == 0 else "fail",
            "returncode": completed.returncode,
            "stderr": _truncate(completed.stderr),
        }
    )
    if not payload.get("failures"):
        payload.pop("stderr", None) if not completed.stderr else None
    return completed.returncode == 0, payload


def _run_declared_test(
    command: Sequence[str],
    isolated_package: Path,
    environment: Mapping[str, str],
    timeout_seconds: float,
) -> tuple[str, dict[str, Any]]:
    try:
        completed = subprocess.run(
            list(command),
            cwd=isolated_package,
            env=dict(environment),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return "timeout", {
            "status": "timeout",
            "timeout_seconds": timeout_seconds,
            "stdout": _truncate(exc.stdout if isinstance(exc.stdout, str) else ""),
            "stderr": _truncate(exc.stderr if isinstance(exc.stderr, str) else ""),
        }
    return ("pass" if completed.returncode == 0 else "fail"), {
        "status": "pass" if completed.returncode == 0 else "fail",
        "returncode": completed.returncode,
        "timeout_seconds": timeout_seconds,
        "stdout": _truncate(completed.stdout),
        "stderr": _truncate(completed.stderr),
    }


def _copy_and_validate_isolation(
    source_package: Path,
    result: PackageResult,
    repo_root: Path,
    maximum_timeout: float,
    root_config: Mapping[str, Any],
) -> None:
    if any(issue.code == E_EXTERNAL_LINK for issue in result.issues):
        result.checks["isolation_copy"] = {"status": "skipped", "reason": "external_link"}
        result.checks["python_compile"] = {"status": "skipped", "reason": "copy_not_safe"}
        result.checks["deterministic_test"] = {"status": "skipped", "reason": "copy_not_safe"}
        return

    try:
        with tempfile.TemporaryDirectory(prefix="standalone-skill-validation-") as temporary:
            isolation_root = Path(temporary)
            discovery_root = isolation_root / "discovery"
            discovery_root.mkdir()
            isolated_package = discovery_root / source_package.name
            shutil.copytree(
                source_package,
                isolated_package,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".git", ".venv", "venv", "node_modules"),
            )
            installed = sorted(path.name for path in discovery_root.iterdir())
            if installed != [source_package.name]:
                raise OSError(f"isolated discovery root contains unexpected entries: {installed!r}")
            if not (isolated_package / "SKILL.md").is_file():
                raise OSError("copied package is missing SKILL.md")
            copied_required_files = ["SKILL.md", "agents/openai.yaml", *result.declared_scripts]
            missing_after_copy = [
                relative
                for relative in copied_required_files
                if not (isolated_package / Path(relative)).is_file()
            ]
            if missing_after_copy:
                raise OSError(
                    "copied package is missing required declared files: "
                    + ", ".join(sorted(set(missing_after_copy)))
                )
            result.checks["isolation_copy"] = {
                "status": "pass",
                "discovery_entries": installed,
                "required_files_verified": sorted(set(copied_required_files)),
            }

            home = isolation_root / "home"
            home.mkdir()
            environment = _isolated_environment(home)
            compile_ok, compile_details = _run_python_compile(
                isolated_package,
                environment,
                maximum_timeout,
            )
            result.checks["python_compile"] = compile_details
            if not compile_ok:
                failures = compile_details.get("failures", [])
                result.add_issue(
                    Issue(
                        E_PYTHON_COMPILE_FAILED,
                        "one or more package-local Python files failed isolated compilation",
                        source_package.name,
                        details={"failures": failures} if failures else compile_details,
                    )
                )

            try:
                declaration, declaration_source = _package_test_declaration(
                    isolated_package,
                    source_package.name,
                    root_config,
                )
                if declaration is None:
                    result.checks["deterministic_test"] = {
                        "status": "not_declared",
                        "fallback": "isolated_python_compile_and_static_import_scan",
                    }
                    return
                raw_command, timeout_seconds = _normalise_test_declaration(declaration, maximum_timeout)
                prepared_command = _prepare_safe_command(raw_command, isolated_package)
            except UnsafeCommandError as exc:
                result.add_issue(
                    Issue(
                        E_TEST_COMMAND_UNSAFE,
                        str(exc),
                        f"{source_package.name}/{declaration_source or 'standalone-validation.json'}",
                    )
                )
                result.checks["deterministic_test"] = {
                    "status": "unsafe",
                    "source": declaration_source,
                }
                return
            except ConfigurationError as exc:
                result.add_issue(
                    Issue(
                        E_TEST_CONFIG_INVALID,
                        str(exc),
                        f"{source_package.name}/{declaration_source or 'standalone-validation.json'}",
                    )
                )
                result.checks["deterministic_test"] = {
                    "status": "invalid",
                    "source": declaration_source,
                }
                return

            if any(issue.code in SAFETY_BLOCKING_CODES for issue in result.issues):
                result.checks["deterministic_test"] = {
                    "status": "skipped",
                    "reason": "static_safety_violation",
                    "source": declaration_source,
                }
                return

            test_status, test_details = _run_declared_test(
                prepared_command,
                isolated_package,
                environment,
                timeout_seconds,
            )
            test_details["source"] = declaration_source
            # Never expose ephemeral absolute paths or the host interpreter in
            # the stable report.  The declared argv is sufficient evidence.
            test_details["declared_command"] = raw_command
            result.checks["deterministic_test"] = test_details
            if test_status == "timeout":
                result.add_issue(
                    Issue(
                        E_TEST_COMMAND_TIMEOUT,
                        "declared deterministic test command timed out",
                        source_package.name,
                        details={"timeout_seconds": timeout_seconds},
                    )
                )
            elif test_status == "fail":
                result.add_issue(
                    Issue(
                        E_TEST_COMMAND_FAILED,
                        "declared deterministic test command returned non-zero",
                        source_package.name,
                        details={
                            "returncode": test_details.get("returncode"),
                            "stdout": test_details.get("stdout", ""),
                            "stderr": test_details.get("stderr", ""),
                        },
                    )
                )
    except (OSError, shutil.Error) as exc:
        result.add_issue(
            Issue(
                E_ISOLATION_COPY_FAILED,
                f"could not copy package into an empty discovery root: {exc}",
                source_package.name,
            )
        )
        result.checks["isolation_copy"] = {"status": "fail"}
        result.checks.setdefault("python_compile", {"status": "skipped", "reason": "copy_failed"})
        result.checks.setdefault("deterministic_test", {"status": "skipped", "reason": "copy_failed"})


def _validate_package(
    package_root: Path,
    all_package_names: Sequence[str],
    repo_root: Path,
    maximum_timeout: float,
    root_config: Mapping[str, Any],
) -> PackageResult:
    result = PackageResult(package_root.name, package_root.name)
    skill_path = package_root / "SKILL.md"
    try:
        skill_text = _read_utf8(skill_path)
        result.checks["skill_md"] = {"status": "pass", "path": "SKILL.md"}
    except (OSError, UnicodeError) as exc:
        result.add_issue(
            Issue(
                E_SKILL_MD_UNREADABLE,
                f"cannot read SKILL.md as UTF-8: {exc}",
                _display_path(skill_path, repo_root),
            )
        )
        result.checks["skill_md"] = {"status": "fail", "path": "SKILL.md"}
        skill_text = ""

    _validate_agent_metadata(package_root, result, repo_root)
    _scan_external_links(package_root, result, repo_root)
    if skill_text:
        _scan_forbidden_markers(skill_path, skill_text, result, repo_root)
        _scan_text_cross_package_paths(
            skill_path,
            skill_text,
            package_root.name,
            all_package_names,
            result,
            repo_root,
        )
        _scan_skill_parent_and_absolute_paths(skill_path, skill_text, result, repo_root)
        _extract_declared_scripts(skill_path, skill_text, package_root, result, repo_root)
    else:
        result.checks["forbidden_release_gate"] = {"status": "skipped"}
        result.checks["declared_scripts"] = {"status": "skipped", "count": 0}

    source_files = _source_files(package_root)
    for source_path in source_files:
        try:
            source_text = _read_utf8(source_path)
        except (OSError, UnicodeError) as exc:
            result.add_issue(
                Issue(
                    E_PYTHON_COMPILE_FAILED if source_path.suffix.casefold() == ".py" else E_REPO_ROOT_PATH,
                    f"cannot read package-local source as UTF-8: {exc}",
                    _display_path(source_path, repo_root),
                )
            )
            continue
        _scan_text_cross_package_paths(
            source_path,
            source_text,
            package_root.name,
            all_package_names,
            result,
            repo_root,
        )
        if source_path.suffix.casefold() == ".py":
            _scan_python_dependencies(
                source_path,
                source_text,
                package_root,
                package_root.name,
                all_package_names,
                result,
                repo_root,
            )
        else:
            _scan_shell_dependencies(source_path, source_text, result, repo_root)

    dependency_issues = [
        issue
        for issue in result.issues
        if issue.code in {E_CROSS_PACKAGE_PATH, E_SIBLING_IMPORT, E_REPO_ROOT_PATH}
    ]
    result.checks["dependency_scan"] = {
        "status": "fail" if dependency_issues else "pass",
        "files_scanned": 1 + len(source_files),
        "python_import_mode": "static_ast",
    }
    _copy_and_validate_isolation(
        package_root,
        result,
        repo_root,
        maximum_timeout,
        root_config,
    )
    return result


def validate_repository(
    repo_root: Path,
    *,
    expected_count: int | None = None,
    maximum_timeout: float = 30.0,
    config_path: Path | None = None,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    if not repo_root.is_dir():
        raise ConfigurationError(f"repository root is not a directory: {repo_root}")
    if maximum_timeout <= 0 or maximum_timeout > 300:
        raise ConfigurationError("timeout must be greater than zero and no more than 300 seconds")
    if expected_count is not None and expected_count < 0:
        raise ConfigurationError("expected package count cannot be negative")

    packages = discover_skill_packages(repo_root)
    package_names = [path.name for path in packages]
    # Dependency scanning includes every visible top-level directory, not only
    # directories with SKILL.md.  This deliberately catches references to
    # repository subsystems such as high-control-ai-tvc.
    sibling_names = sorted(
        child.name
        for child in repo_root.iterdir()
        if child.is_dir() and not child.name.startswith(".")
    )
    root_config = _load_root_test_config(config_path, repo_root)
    unknown_config_packages = sorted(set(root_config) - set(package_names))
    global_issues: list[Issue] = []
    if not packages:
        global_issues.append(Issue(E_NO_SKILL_PACKAGES, "no top-level directories containing SKILL.md were found"))
    if expected_count is not None and len(packages) != expected_count:
        global_issues.append(
            Issue(
                E_PACKAGE_COUNT_MISMATCH,
                f"expected {expected_count} top-level Skill packages but discovered {len(packages)}",
                details={"expected": expected_count, "actual": len(packages)},
            )
        )
    if unknown_config_packages:
        global_issues.append(
            Issue(
                E_TEST_CONFIG_INVALID,
                "root test configuration contains unknown package names",
                details={"unknown_packages": unknown_config_packages},
            )
        )

    package_results = [
        _validate_package(
            package,
            sibling_names,
            repo_root,
            maximum_timeout,
            root_config,
        )
        for package in packages
    ]
    failed_packages = sum(bool(result.issues) for result in package_results)
    total_issues = len(global_issues) + sum(len(result.issues) for result in package_results)
    status = "pass" if total_issues == 0 else "fail"
    exit_code = EXIT_OK if status == "pass" else EXIT_VALIDATION_FAILED
    return {
        "schema_version": SCHEMA_VERSION,
        "validator": "standalone-skill-isolation",
        "repo_root": str(repo_root),
        "status": status,
        "exit_code": exit_code,
        "summary": {
            "packages_total": len(package_results),
            "packages_passed": len(package_results) - failed_packages,
            "packages_failed": failed_packages,
            "issues_total": total_issues,
        },
        "packages": [result.as_dict() for result in package_results],
        "issues": [issue.as_dict() for issue in global_issues],
    }


def _write_report(report: Mapping[str, Any], output: Path | None, compact: bool) -> None:
    indent = None if compact else 2
    rendered = json.dumps(report, ensure_ascii=False, indent=indent, sort_keys=True) + "\n"
    sys.stdout.write(rendered)
    if output is not None:
        output_path = output.resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = output_path.with_name(output_path.name + ".tmp")
        temporary_path.write_text(rendered, encoding="utf-8", newline="\n")
        temporary_path.replace(output_path)


def _configuration_error_report(message: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "validator": "standalone-skill-isolation",
        "status": "error",
        "exit_code": EXIT_CONFIGURATION_ERROR,
        "summary": {
            "packages_total": 0,
            "packages_passed": 0,
            "packages_failed": 0,
            "issues_total": 1,
        },
        "packages": [],
        "issues": [{"code": E_TEST_CONFIG_INVALID, "message": message}],
    }


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    default_root = Path(__file__).resolve().parents[2]
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=default_root,
        help="repository root (defaults to two levels above this script)",
    )
    parser.add_argument(
        "--expected-count",
        type=int,
        default=None,
        help="optional exact package-count assertion (use 16 for this repository)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="maximum seconds for each isolated compile/test command (1-300; default 30)",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="optional JSON mapping of package names to deterministic test declarations",
    )
    parser.add_argument("--output", type=Path, default=None, help="optional path to also write the JSON report")
    parser.add_argument("--compact", action="store_true", help="emit compact JSON")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_argument_parser()
    args = parser.parse_args(argv)
    try:
        report = validate_repository(
            args.repo_root,
            expected_count=args.expected_count,
            maximum_timeout=args.timeout,
            config_path=args.config,
        )
    except ConfigurationError as exc:
        report = _configuration_error_report(str(exc))
        _write_report(report, args.output, args.compact)
        return EXIT_CONFIGURATION_ERROR
    except Exception as exc:  # pragma: no cover - last-resort machine-readable failure
        report = {
            "schema_version": SCHEMA_VERSION,
            "validator": "standalone-skill-isolation",
            "status": "error",
            "exit_code": EXIT_INTERNAL_ERROR,
            "summary": {
                "packages_total": 0,
                "packages_passed": 0,
                "packages_failed": 0,
                "issues_total": 1,
            },
            "packages": [],
            "issues": [{"code": "E_INTERNAL_VALIDATOR_ERROR", "message": f"{type(exc).__name__}: {exc}"}],
        }
        _write_report(report, args.output, args.compact)
        return EXIT_INTERNAL_ERROR
    _write_report(report, args.output, args.compact)
    return int(report["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
