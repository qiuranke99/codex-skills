#!/usr/bin/env python3
"""Validate one real PROJECT_CANON pre->post atomic transition.

The post manifest and the ordinary update receipt prove only the resulting
registry.  This validator additionally requires the immutable base snapshot
bytes and therefore can enforce ownership, preservation and monotonic-history
rules across the actual transition.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

from validate_manifest_update_receipt import validate_receipt
from validate_project_canon_manifest import canonical_hash, validate_manifest


SHA = re.compile(r"^[a-f0-9]{64}$")
SHOT_OWNER = "ai-video-shot-script-director"
OTHER_OWNER_STALE_FIELDS = {"approval_status", "stale_reason", "eligible_for_downstream"}
ROOT_MUTABLE_FIELDS = {
    "version", "sha256", "current_phase", "revision_counter", "updated_by_skill",
    "base_manifest_sha256", "active_artifacts", "superseded_artifacts",
    "dependency_edges", "stale_events", "unresolved_change_requests",
}


def _semver(value: Any) -> tuple[int, int, int] | None:
    if not isinstance(value, str):
        return None
    parts = value.split(".")
    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        return None
    return tuple(int(part) for part in parts)  # type: ignore[return-value]


def _by_id(values: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(values, list):
        return {}
    return {item["artifact_id"]: item for item in values if isinstance(item, dict) and isinstance(item.get("artifact_id"), str)}


def _events_by_id(values: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(values, list):
        return {}
    return {item["event_id"]: item for item in values if isinstance(item, dict) and isinstance(item.get("event_id"), str)}


def validate_transition(
    base: dict[str, Any],
    post: dict[str, Any],
    updated_by_skill: str,
    receipt: dict[str, Any] | None = None,
    expected_registered_ids: set[str] | None = None,
    preserved_artifact_ids: set[str] | None = None,
) -> list[str]:
    errors: list[str] = []
    errors.extend(f"base manifest invalid: {item}" for item in validate_manifest(base))
    errors.extend(f"post manifest invalid: {item}" for item in validate_manifest(post))
    if base.get("approval_status") == "draft" or post.get("approval_status") == "draft":
        errors.append("base and post manifests must both be frozen canonical snapshots")
    if base.get("sha256") != canonical_hash(base):
        errors.append("base snapshot canonical sha256 mismatch")
    if post.get("sha256") != canonical_hash(post):
        errors.append("post manifest canonical sha256 mismatch")
    if post.get("base_manifest_sha256") != base.get("sha256"):
        errors.append("post base_manifest_sha256 must equal the actual base snapshot canonical hash")
    if post.get("updated_by_skill") != updated_by_skill:
        errors.append("post updated_by_skill does not equal the declared updater")
    if not isinstance(base.get("revision_counter"), int) or post.get("revision_counter") != base.get("revision_counter") + 1:
        errors.append("post revision_counter must equal base revision_counter + 1")
    before_version, after_version = _semver(base.get("version")), _semver(post.get("version"))
    if before_version is None or after_version is None or after_version <= before_version:
        errors.append("post manifest SemVer must be greater than base manifest SemVer")

    for field in set(base) | set(post):
        if field in ROOT_MUTABLE_FIELDS:
            continue
        if field in {"canonical_shot_uids", "affected_shot_uids"} and updated_by_skill == SHOT_OWNER:
            continue
        if base.get(field) != post.get(field):
            errors.append(f"transition changed immutable root field {field}")

    base_active = _by_id(base.get("active_artifacts"))
    post_active = _by_id(post.get("active_artifacts"))
    base_history = _by_id(base.get("superseded_artifacts"))
    post_history = _by_id(post.get("superseded_artifacts"))

    for artifact_id, old in base_history.items():
        if post_history.get(artifact_id) != old:
            errors.append(f"immutable superseded history changed or disappeared: {artifact_id}")

    changed_owned_ids: set[str] = set()
    other_owner_stale_ids: set[str] = set()
    for artifact_id, old in base_active.items():
        new = post_active.get(artifact_id)
        if old.get("owner_skill") == updated_by_skill:
            if new != old:
                if new is not None:
                    changed_owned_ids.add(artifact_id)
            if new is None:
                archived = post_history.get(artifact_id)
                if not isinstance(archived, dict):
                    errors.append(f"removed owned active artifact lacks immutable superseded entry: {artifact_id}")
                else:
                    for field, value in old.items():
                        if field == "eligible_for_downstream":
                            if archived.get(field) is not False:
                                errors.append(f"superseded owned artifact must become downstream-ineligible: {artifact_id}")
                        elif archived.get(field) != value:
                            errors.append(f"superseded entry rewrote prior owned artifact field {field}: {artifact_id}")
        else:
            if new is None:
                errors.append(f"updater removed artifact owned by another skill: {artifact_id}")
                continue
            changed_fields = {field for field in set(old) | set(new) if old.get(field) != new.get(field)}
            if changed_fields - OTHER_OWNER_STALE_FIELDS:
                errors.append(
                    f"updater changed another owner's artifact content/identity {artifact_id}: "
                    + ", ".join(sorted(changed_fields - OTHER_OWNER_STALE_FIELDS))
                )
            if changed_fields:
                if (
                    new.get("approval_status") not in {"stale", "blocked"}
                    or new.get("eligible_for_downstream") is not False
                    or not isinstance(new.get("stale_reason"), str)
                    or not new["stale_reason"].strip()
                ):
                    errors.append(f"another-owner artifact may change only to a complete stale/blocked registry state: {artifact_id}")
                else:
                    other_owner_stale_ids.add(artifact_id)

    for artifact_id, new in post_active.items():
        if artifact_id not in base_active:
            if new.get("owner_skill") != updated_by_skill:
                errors.append(f"updater registered new artifact owned by another skill: {artifact_id}")
            else:
                changed_owned_ids.add(artifact_id)

    for artifact_id, new in post_history.items():
        if artifact_id not in base_history and new.get("owner_skill") != updated_by_skill:
            errors.append(f"updater appended superseded history owned by another skill: {artifact_id}")

    base_events = _events_by_id(base.get("stale_events"))
    post_events = _events_by_id(post.get("stale_events"))
    for event_id, event in base_events.items():
        if post_events.get(event_id) != event:
            errors.append(f"immutable stale event changed or disappeared: {event_id}")
    new_events = [event for event_id, event in post_events.items() if event_id not in base_events]
    for artifact_id in other_owner_stale_ids:
        matching = [
            event for event in new_events
            if artifact_id in event.get("stale_artifact_ids", [])
            and event.get("changed_artifact_id") in changed_owned_ids
            and event.get("affected_shot_uids") == post_active[artifact_id].get("affected_shot_uids")
        ]
        if len(matching) != 1:
            errors.append(f"another-owner stale registry change requires exactly one new complete stale_event: {artifact_id}")

    registered_ids = expected_registered_ids
    if receipt is not None:
        receipt_ids = receipt.get("registered_artifact_ids")
        receipt_set = set(receipt_ids) if isinstance(receipt_ids, list) and all(isinstance(item, str) for item in receipt_ids) else set()
        errors.extend(validate_receipt(receipt, updated_by_skill, registered_ids, post))
        if registered_ids is None:
            registered_ids = receipt_set
    if registered_ids is not None and registered_ids != changed_owned_ids:
        errors.append(
            "registered_artifact_ids must exactly equal new/changed updater-owned active artifacts: "
            f"expected {sorted(changed_owned_ids)}, got {sorted(registered_ids)}"
        )

    for artifact_id in preserved_artifact_ids or set():
        if artifact_id not in base_active:
            errors.append(f"declared preserved artifact was not active in base snapshot: {artifact_id}")
        elif post_active.get(artifact_id) != base_active[artifact_id]:
            errors.append(f"declared preserved artifact changed across transition: {artifact_id}")

    return errors


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} root must be an object")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base_snapshot", type=Path)
    parser.add_argument("post_manifest", type=Path)
    parser.add_argument("--base-snapshot-file-sha256", required=True)
    parser.add_argument("--updated-by-skill", required=True)
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--expected-registered-artifact-id", action="append", default=[])
    parser.add_argument("--preserved-artifact-id", action="append", default=[])
    args = parser.parse_args()
    try:
        actual_snapshot_file_hash = hashlib.sha256(args.base_snapshot.read_bytes()).hexdigest()
        if not SHA.fullmatch(args.base_snapshot_file_sha256) or actual_snapshot_file_hash != args.base_snapshot_file_sha256:
            print("ERROR: base snapshot raw file SHA-256 mismatch")
            return 1
        base = _load(args.base_snapshot)
        post = _load(args.post_manifest)
        receipt = _load(args.receipt) if args.receipt else None
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: transition inputs unreadable: {exc}")
        return 2
    expected = set(args.expected_registered_artifact_id) if args.expected_registered_artifact_id else None
    errors = validate_transition(
        base,
        post,
        args.updated_by_skill,
        receipt,
        expected,
        set(args.preserved_artifact_id),
    )
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("OK: PROJECT_CANON atomic pre->post transition is valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
