#!/usr/bin/env python3
"""Validate a standalone Prompt P1 package before K2 or V2 production."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import validate_prompt_package as shared


SHOT_SCRIPT_ROOT = Path(__file__).resolve().parents[2] / "ai-video-shot-script-director" / "scripts"
if str(SHOT_SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SHOT_SCRIPT_ROOT))
from build_asset_canon_export import validate_export_record as validate_owner_asset_export


P1_REQUIRED_FILES = (
    shared.PREFLIGHT_SNAPSHOT,
    shared.PREFLIGHT_PLAN,
    shared.MODEL_CAPS,
    shared.PROVIDER_CAPS,
)
DEFAULT_CANON = "00_project_canon/PROJECT_CANON_MANIFEST.json"


def load_object(path: Path, label: str) -> tuple[dict[str, Any] | None, list[str]]:
    try:
        value = shared.load_json(path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return None, [f"{label}: unreadable JSON: {exc}"]
    if not isinstance(value, dict):
        return None, [f"{label}: top-level JSON object required"]
    return value, []


def resolve_project_file(project_root: Path, locator: Any, label: str) -> tuple[Path | None, list[str]]:
    if not isinstance(locator, str) or not locator:
        return None, [f"{label}: non-empty project-relative locator required"]
    relative = Path(locator)
    if relative.is_absolute() or ".." in relative.parts:
        return None, [f"{label}: absolute paths and traversal are forbidden"]
    candidate = (project_root / relative).resolve()
    try:
        candidate.relative_to(project_root.resolve())
    except (OSError, ValueError):
        return None, [f"{label}: locator escapes project root"]
    return candidate, []


def verify_hash_locked_file(project_root: Path, locator: Any, digest: Any, label: str) -> tuple[Path | None, list[str]]:
    path, errors = resolve_project_file(project_root, locator, label)
    if path is None:
        return None, errors
    if not path.is_file():
        return path, errors + [f"{label}: file missing"]
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != actual:
        errors.append(f"{label}: file SHA-256 mismatch")
    return path, errors


def verify_canon_entry_files(
    project_root: Path, active: dict[str, dict[str, Any]]
) -> tuple[list[str], dict[str, list[str]]]:
    errors: list[str] = []
    fixed_owner_roles: dict[str, list[str]] = {}
    for artifact_id, entry in active.items():
        label = f"preflight Canon/{artifact_id}"
        if entry.get("eligible_for_downstream") is not True:
            errors.append(f"{label}: active artifact must be downstream-eligible for a ready P1")
        if entry.get("approval_status") not in {"assistant_validated", "user_approved"} or entry.get("stale_reason") is not None:
            errors.append(f"{label}: active artifact must be approved and non-stale for a ready P1")
        primary_path, primary_errors = verify_hash_locked_file(
            project_root, entry.get("locator"), entry.get("file_sha256"), f"{label}/primary"
        )
        errors.extend(primary_errors)
        record_path, record_errors = verify_hash_locked_file(
            project_root,
            entry.get("artifact_record_locator"),
            entry.get("artifact_record_file_sha256"),
            f"{label}/artifact record",
        )
        errors.extend(record_errors)
        if primary_path is None or record_path is None or not record_path.is_file():
            continue
        record, parse_errors = load_object(record_path, f"{label}/artifact record")
        errors.extend(parse_errors)
        if record is None:
            continue
        errors.extend(shared.validate_envelope(record, f"{label}/artifact record", entry.get("owner_skill")))
        if entry.get("owner_skill") in shared.REGISTERED_ASSET_OWNERS:
            errors.extend(
                f"{label}/fixed-owner export: {error}"
                for error in validate_owner_asset_export(record, project_root)
            )
            authorized_roles = record.get("control_roles_authorized")
            if isinstance(authorized_roles, list) and all(isinstance(role, str) for role in authorized_roles):
                fixed_owner_roles[artifact_id] = list(authorized_roles)
        expected = {
            "artifact_id": entry.get("artifact_id"),
            "owner_skill": entry.get("owner_skill"),
            "version": entry.get("version"),
            "sha256": entry.get("sha256"),
            "approval_status": entry.get("approval_status"),
            "dependencies": entry.get("dependencies"),
            "affected_shot_uids": entry.get("affected_shot_uids"),
            "stale_reason": entry.get("stale_reason"),
        }
        if any(record.get(field) != value for field, value in expected.items()):
            errors.append(f"{label}: artifact record envelope differs from active Canon")
    return errors, fixed_owner_roles


def validate_capability_doc_binding(
    root: Path,
    project_root: Path,
    active: dict[str, dict[str, Any]],
    document: dict[str, Any],
    relative_path: str,
    expected_slot: str,
    label: str,
) -> list[str]:
    errors: list[str] = []
    entry = next((item for item in active.values() if item.get("artifact_slot") == expected_slot), None)
    if not isinstance(entry, dict):
        return [f"{label}: active Canon slot {expected_slot} missing"]
    if shared.artifact_ref(document) != shared.artifact_ref(entry):
        errors.append(f"{label}: package capability artifact differs from active Canon ref")
    expected_locator = (root / relative_path).resolve().relative_to(project_root.resolve()).as_posix()
    actual_file_hash = hashlib.sha256((root / relative_path).read_bytes()).hexdigest()
    if entry.get("locator") != expected_locator or entry.get("file_sha256") != actual_file_hash:
        errors.append(f"{label}: package capability bytes differ from active Canon primary lock")
    if entry.get("artifact_record_locator") != expected_locator or entry.get("artifact_record_file_sha256") != actual_file_hash:
        errors.append(f"{label}: package capability bytes differ from active Canon record lock")
    return errors


def _validate_preflight_package(root: Path, project_root: Path, canon_path: Path) -> list[str]:
    errors: list[str] = []
    for relative in P1_REQUIRED_FILES:
        if not (root / relative).is_file():
            errors.append(f"missing P1 file: {relative}")
    if errors:
        return errors

    snapshot, snapshot_read_errors = load_object(root / shared.PREFLIGHT_SNAPSHOT, "preflight Canon snapshot")
    plan, plan_read_errors = load_object(root / shared.PREFLIGHT_PLAN, "P1 plan")
    model_doc, model_read_errors = load_object(root / shared.MODEL_CAPS, "model capability profile")
    provider_doc, provider_read_errors = load_object(root / shared.PROVIDER_CAPS, "provider capability profile")
    errors.extend(snapshot_read_errors + plan_read_errors + model_read_errors + provider_read_errors)
    if not all(isinstance(item, dict) for item in (snapshot, plan, model_doc, provider_doc)):
        return errors
    assert snapshot is not None and plan is not None and model_doc is not None and provider_doc is not None

    reference_root = Path(__file__).resolve().parents[1] / "references"
    for document, schema_name, label in (
        (plan, "generation_unit_preflight.schema.json", "P1 plan"),
        (model_doc, "capability_profile.schema.json", "model capability profile"),
        (provider_doc, "capability_profile.schema.json", "provider capability profile"),
    ):
        schema, schema_errors = load_object(reference_root / schema_name, f"{label} schema")
        errors.extend(schema_errors)
        if schema is not None:
            errors.extend(f"{label}: schema: {item}" for item in shared.validate_instance(document, schema, schema))

    snapshot_errors, active = shared.validate_manifest_snapshot(snapshot, "preflight Canon snapshot")
    errors.extend(snapshot_errors)
    errors.extend(shared.validate_manifest_receipt(
        root, plan.get("project_canon_read_receipt"), snapshot, shared.PREFLIGHT_SNAPSHOT, "P1 plan"
    ))
    if plan.get("project_id") != snapshot.get("project_id"):
        errors.append("P1 plan: project_id differs from preflight Canon snapshot")

    expected_canon = (project_root / DEFAULT_CANON).resolve()
    if canon_path.resolve() != expected_canon:
        errors.append("P1 source Canon: CLI path must be <project_root>/00_project_canon/PROJECT_CANON_MANIFEST.json")
    actual_canon, canon_read_errors = load_object(canon_path, "P1 source Canon")
    errors.extend(canon_read_errors)
    if actual_canon is not None and actual_canon != snapshot:
        errors.append("P1 source Canon: actual canonical manifest must exactly equal the frozen preflight snapshot")
    canon_file_errors, fixed_owner_roles = verify_canon_entry_files(project_root, active)
    errors.extend(canon_file_errors)

    errors.extend(validate_capability_doc_binding(
        root, project_root, active, model_doc, shared.MODEL_CAPS, "model_capability", "model capability profile"
    ))
    errors.extend(validate_capability_doc_binding(
        root, project_root, active, provider_doc, shared.PROVIDER_CAPS, "provider_capability", "provider capability profile"
    ))

    basic_plan_errors, _ = shared.validate_preflight_plan(root, plan, snapshot, active)
    errors.extend(basic_plan_errors)
    capability_errors, provider, effective_limits = shared.validate_capabilities(root, model_doc, provider_doc)
    errors.extend(capability_errors)
    if isinstance(provider, dict):
        if plan.get("provider_profile_id") != provider.get("profile_id"):
            errors.append("P1 plan: provider_profile_id differs from the verified provider profile")
        if plan.get("documented_backend_profile_id") != provider.get("documented_backend_profile_id"):
            errors.append("P1 plan: documented backend differs from the verified provider binding")
    errors.extend(shared.validate_preflight_decision_matrix(
        plan, active, provider, effective_limits,
        fixed_owner_roles=fixed_owner_roles, project_root=project_root,
    ))
    if plan.get("plan_status") != "ready_for_boundary_supplement":
        errors.append("P1 plan: standalone success requires ready_for_boundary_supplement")
    if plan.get("approval_status") not in {"assistant_validated", "user_approved"}:
        errors.append("P1 plan: standalone success requires assistant_validated or user_approved")
    if plan.get("blocked_reasons") != []:
        errors.append("P1 plan: standalone success requires an empty blocked_reasons list")
    return errors


def validate_preflight_package(root: Path, project_root: Path, canon_path: Path) -> list[str]:
    root = root.resolve()
    project_root = project_root.resolve()
    if root == project_root:
        return ["P1 package root must be a strict child of --project-root"]
    try:
        root.relative_to(project_root)
        canon_path.resolve().relative_to(project_root)
    except (OSError, ValueError):
        return ["P1 package and source Canon must be inside --project-root"]
    try:
        return _validate_preflight_package(root, project_root, canon_path.resolve())
    except (TypeError, KeyError, AttributeError, ValueError, OverflowError) as exc:
        return [f"malformed P1 package rejected safely: {type(exc).__name__}: {exc}"]


def main(argv: list[str]) -> int:
    if len(argv) != 6 or argv[2] != "--project-root" or argv[4] != "--project-canon-manifest":
        print(
            "usage: validate_preflight_package.py <package_root> --project-root <project_root> "
            "--project-canon-manifest <source-canon.json>",
            file=sys.stderr,
        )
        return 2
    errors = validate_preflight_package(Path(argv[1]), Path(argv[3]), Path(argv[5]))
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        print(f"FAILED: {len(errors)} error(s)")
        return 1
    print("PASS: standalone Prompt P1 package is valid and ready for K2/V2")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
