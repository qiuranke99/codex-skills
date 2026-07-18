#!/usr/bin/env python3
"""Shared standard-library helpers for the reference research run contract."""

from __future__ import annotations

import json
import math
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path, PurePath
from typing import Any, Iterable


class ContractError(ValueError):
    """Raised when an artifact cannot be parsed as a contract artifact."""


def canonical_relative_path(path: str | PurePath, root: str | PurePath) -> str:
    """Render one root-relative contract path with platform-neutral separators."""

    candidate = path if isinstance(path, PurePath) else Path(path)
    base = root if isinstance(root, PurePath) else Path(root)
    try:
        return candidate.relative_to(base).as_posix()
    except ValueError as exc:
        raise ContractError(f"artifact path {candidate} is outside root {base}") from exc


def _reject_constant(token: str) -> Any:
    raise ValueError(f"non-standard JSON number is forbidden: {token}")


def _finite_float(token: str) -> float:
    value = float(token)
    if not math.isfinite(value):
        raise ValueError(f"non-finite JSON number is forbidden: {token}")
    return value


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON object key is forbidden: {key}")
        result[key] = value
    return result


def strict_json_loads(source: str) -> Any:
    return json.loads(
        source,
        parse_constant=_reject_constant,
        parse_float=_finite_float,
        object_pairs_hook=_unique_object,
    )


def read_json(path: str | Path) -> Any:
    artifact = Path(path)
    try:
        return strict_json_loads(artifact.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise ContractError(f"cannot read JSON {artifact}: {exc}") from exc


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    artifact = Path(path)
    rows: list[dict[str, Any]] = []
    try:
        for line_no, raw in enumerate(artifact.read_text(encoding="utf-8").splitlines(), 1):
            if not raw.strip():
                continue
            value = strict_json_loads(raw)
            if not isinstance(value, dict):
                raise ContractError(f"{artifact}:{line_no} must contain a JSON object")
            rows.append(value)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise ContractError(f"cannot read JSONL {artifact}: {exc}") from exc
    return rows


def read_records(path: str | Path) -> list[dict[str, Any]]:
    artifact = Path(path)
    if artifact.suffix.lower() == ".jsonl":
        return read_jsonl(artifact)
    value = read_json(artifact)
    if isinstance(value, list):
        records = value
    elif isinstance(value, dict):
        records = value.get("items", value.get("candidates", value.get("receipts", [])))
    else:
        records = []
    if not isinstance(records, list) or not all(isinstance(item, dict) for item in records):
        raise ContractError(f"{artifact} does not contain an object list")
    return records


def same_artifact(left: str | Path, right: str | Path) -> bool:
    """Compare artifact identities after expansion and symlink resolution."""

    try:
        return Path(left).expanduser().resolve(strict=False) == Path(right).expanduser().resolve(strict=False)
    except (OSError, RuntimeError) as exc:
        raise ContractError(f"cannot safely resolve artifact identity: {exc}") from exc


def write_text_atomic(path: str | Path, rendered: str) -> None:
    """Replace one regular artifact atomically without following a leaf symlink."""

    artifact = Path(path)
    temporary: Path | None = None
    try:
        artifact.parent.mkdir(parents=True, exist_ok=True)
        if artifact.is_symlink():
            raise ContractError(f"refusing to replace symlink artifact {artifact}")
        existing_mode = artifact.stat().st_mode & 0o777 if artifact.exists() else 0o644
        descriptor, raw_temporary = tempfile.mkstemp(
            dir=artifact.parent,
            prefix=f".{artifact.name}.",
            suffix=".tmp",
            text=True,
        )
        temporary = Path(raw_temporary)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
                handle.write(rendered)
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temporary, existing_mode)
            os.replace(temporary, artifact)
            temporary = None
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
    except ContractError:
        raise
    except OSError as exc:
        raise ContractError(f"cannot atomically write {artifact}: {exc}") from exc


def write_json(path: str | Path, value: Any) -> None:
    artifact = Path(path)
    try:
        rendered = json.dumps(
            value, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False
        ) + "\n"
    except (TypeError, ValueError, OverflowError) as exc:
        raise ContractError(f"cannot serialize strict JSON {artifact}: {exc}") from exc
    write_text_atomic(artifact, rendered)


def write_jsonl(path: str | Path, rows: Iterable[dict[str, Any]]) -> None:
    artifact = Path(path)
    try:
        rendered = "".join(
            json.dumps(row, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n"
            for row in rows
        )
    except (TypeError, ValueError, OverflowError) as exc:
        raise ContractError(f"cannot serialize strict JSONL {artifact}: {exc}") from exc
    write_text_atomic(artifact, rendered)


def parse_timestamp(value: Any, field_name: str = "timestamp") -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ContractError(f"{field_name} must be a non-empty ISO-8601 string")
    raw = value.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise ContractError(f"{field_name} is not valid ISO-8601: {value}") from exc
    if parsed.tzinfo is None:
        raise ContractError(f"{field_name} must include a timezone: {value}")
    return parsed.astimezone(timezone.utc)


def get_path(value: dict[str, Any], *paths: str, default: Any = None) -> Any:
    """Return the first present dotted path, allowing narrow schema evolution."""

    for path in paths:
        cursor: Any = value
        found = True
        for segment in path.split("."):
            if not isinstance(cursor, dict) or segment not in cursor:
                found = False
                break
            cursor = cursor[segment]
        if found:
            return cursor
    return default


def selection_ids(artifact: dict[str, Any]) -> list[str]:
    raw = artifact.get("candidate_ids", artifact.get("items", []))
    if not isinstance(raw, list):
        raise ContractError("selection candidate_ids/items must be a list")
    result: list[str] = []
    for item in raw:
        if isinstance(item, str):
            candidate_id = item
        elif isinstance(item, dict):
            candidate_id = item.get("candidate_id", item.get("id"))
        else:
            candidate_id = None
        if not isinstance(candidate_id, str) or not candidate_id:
            raise ContractError("selection entry is missing candidate_id")
        result.append(candidate_id)
    return result


def bool_is(value: Any, expected: bool) -> bool:
    return isinstance(value, bool) and value is expected
