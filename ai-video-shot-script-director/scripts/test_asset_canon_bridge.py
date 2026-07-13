#!/usr/bin/env python3
"""Synthetic positive and adversarial tests for all seven legacy asset owners."""

from __future__ import annotations

import copy
import contextlib
import binascii
import builtins
import hashlib
import importlib.util
import io
import json
import os
import struct
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path
from typing import Any

from build_asset_canon_export import ExportError, OWNER_PROFILES, _image_metadata, _safe_locator, validate_export_record
from validate_project_canon_manifest import canonical_hash, validate_manifest, verify_artifact_files


SKILL_ROOT = Path(__file__).resolve().parents[2]
WRAPPERS = {
    profile_id: SKILL_ROOT / profile.owner_skill / "scripts/export_ai_video_canon.py"
    for profile_id, profile in OWNER_PROFILES.items()
}
EXPORT_VALIDATOR = SKILL_ROOT / "ai-video-shot-script-director/scripts/validate_asset_canon_export.py"


def write_bytes(root: Path, locator: str, data: bytes) -> str:
    path = root / locator
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def write_json(root: Path, locator: str, value: dict[str, Any]) -> str:
    return write_bytes(
        root,
        locator,
        (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8"),
    )


def make_png(width: int = 64, height: int = 64) -> bytes:
    def chunk(kind: bytes, payload: bytes) -> bytes:
        body = kind + payload
        return struct.pack(">I", len(payload)) + body + struct.pack(">I", binascii.crc32(body) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    scanlines = b"".join(b"\x00" + (b"\x20\x40\x60" * width) for _ in range(height))
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(scanlines)) + chunk(b"IEND", b"")


def make_forged_header_png() -> bytes:
    def chunk(kind: bytes, payload: bytes) -> bytes:
        body = kind + payload
        return struct.pack(">I", len(payload)) + body + struct.pack(">I", binascii.crc32(body) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", 1024, 1024, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(b"x")) + chunk(b"IEND", b"")


def initialize_project(root: Path) -> None:
    shot_record: dict[str, Any] = {
        "contract_version": "ai-video-artifact-v1",
        "artifact_id": "SHOT_CONTRACT_SYNTHETIC",
        "owner_skill": "ai-video-shot-script-director",
        "version": "1.0.0",
        "sha256": None,
        "approval_status": "assistant_validated",
        "dependencies": [],
        "affected_shot_uids": ["S001", "S002"],
        "stale_reason": None,
    }
    shot_record["sha256"] = canonical_hash(shot_record)
    shot_file_hash = write_json(root, "artifacts/SHOT_CONTRACT_SYNTHETIC.json", shot_record)
    shot_entry = {
        "artifact_slot": "professional_shot_contract",
        "artifact_id": shot_record["artifact_id"],
        "artifact_type": "PROFESSIONAL_SHOT_CONTRACT",
        "owner_skill": shot_record["owner_skill"],
        "version": shot_record["version"],
        "sha256": shot_record["sha256"],
        "approval_status": shot_record["approval_status"],
        "stale_reason": None,
        "eligible_for_downstream": True,
        "affected_shot_uids": ["S001", "S002"],
        "locator": "artifacts/SHOT_CONTRACT_SYNTHETIC.json",
        "file_sha256": shot_file_hash,
        "artifact_record_locator": "artifacts/SHOT_CONTRACT_SYNTHETIC.json",
        "artifact_record_file_sha256": shot_file_hash,
        "dependencies": [],
    }
    manifest: dict[str, Any] = {
        "contract_version": "ai-video-artifact-v1",
        "artifact_id": "PROJECT_CANON_MANIFEST_BRIDGE_TEST",
        "owner_skill": "ai-video-shot-script-director",
        "version": "1.0.0",
        "sha256": None,
        "approval_status": "assistant_validated",
        "dependencies": [],
        "affected_shot_uids": ["S001", "S002"],
        "stale_reason": None,
        "schema_version": "ai-video-project-canon-manifest.v1",
        "project_id": "BRIDGE_TEST",
        "manifest_role": "artifact_registry_only",
        "manifest_update_policy": "validated_atomic_delta_no_reverse_dependency",
        "current_phase": "professional_script",
        "revision_counter": 1,
        "updated_by_skill": "ai-video-shot-script-director",
        "base_manifest_sha256": None,
        "canonical_shot_uids": ["S001", "S002"],
        "active_artifacts": [shot_entry],
        "superseded_artifacts": [],
        "dependency_edges": [],
        "stale_events": [],
        "unresolved_change_requests": [],
    }
    manifest["sha256"] = canonical_hash(manifest)
    write_json(root, "00_project_canon/PROJECT_CANON_MANIFEST.json", manifest)


def load_packaging_fixture_module() -> Any:
    scripts = SKILL_ROOT / "packaging-product-identity-label-lock-board/scripts"
    module_path = scripts / "test_contract.py"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    spec = importlib.util.spec_from_file_location("_packaging_contract_fixture", module_path)
    if spec is None or spec.loader is None:
        raise AssertionError("packaging fixture module is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def create_packaging_exact_copy_run_and_evidence(
    root: Path,
    prefix: str,
    asset_key: str,
) -> dict[str, str]:
    """Build one fully validated COMPLETE run and bind its primary master."""
    fixture = load_packaging_fixture_module()
    run_root = root / prefix / "complete_packaging_run"
    fixture.create_complete_run(run_root)
    run_errors = fixture.validate_run(run_root)
    if run_errors:
        raise AssertionError(f"packaging exact-copy fixture invalid: {run_errors}")
    manifest_path = run_root / "00_manifest/run_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    asset_qa_path = run_root / manifest["paths"]["asset_qa"]
    asset_qa = json.loads(asset_qa_path.read_text(encoding="utf-8"))
    primary = next(item for item in asset_qa["assets"] if item["view_id"] == "ROT_0000")
    post_path = run_root / manifest["paths"]["post_composite_verification"]
    post = json.loads(post_path.read_text(encoding="utf-8"))
    post_result = next(
        item for item in post["asset_results"]
        if item["asset_id"] == primary["asset_id"] and item["view_id"] == primary["view_id"]
    )
    run_root_locator = run_root.relative_to(root).as_posix()
    primary_locator = (Path(run_root_locator) / primary["file_path"]).as_posix()
    role_mapping = {
        "exact_copy_bundle": ("exact_copy_bundle", "exact_copy_bundle_file_sha256"),
        "coverage_matrix": ("coverage_matrix", "coverage_matrix_sha256"),
        "generation_prompt_index": ("generation_prompt_index", "generation_prompt_index_sha256"),
        "asset_qa": ("asset_qa", "asset_qa_sha256"),
        "continuity_qa": ("continuity_qa", "continuity_qa_sha256"),
        "post_composite_verification": (
            "post_composite_verification", "post_composite_verification_sha256"
        ),
    }
    locks = {
        role: {
            "locator": (Path(run_root_locator) / manifest["paths"][path_key]).as_posix(),
            "file_sha256": manifest["hashes"][hash_key],
        }
        for role, (path_key, hash_key) in role_mapping.items()
    }
    validator_path = (
        SKILL_ROOT
        / "packaging-product-identity-label-lock-board/scripts/validate_packaging_run.py"
    )
    evidence = {
        "schema_version": "packaging-exact-copy-canon-evidence.v2",
        "owner_skill": "packaging-product-identity-label-lock-board",
        "asset_key": asset_key,
        "primary_asset_sha256": primary["file_sha256"],
        "packaging_run": {
            "run_root_locator": run_root_locator,
            "run_manifest_locator": (Path(run_root_locator) / "00_manifest/run_manifest.json").as_posix(),
            "run_manifest_file_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
            "run_id": manifest["run_id"],
            "contract_version": manifest["contract_version"],
        },
        "validator_file_sha256": hashlib.sha256(validator_path.read_bytes()).hexdigest(),
        "run_artifact_locks": locks,
        "primary_member": {
            "asset_id": primary["asset_id"], "view_id": primary["view_id"],
            "locator": primary_locator, "file_sha256": primary["file_sha256"],
            "post_result_id": post_result["result_id"],
            "post_result_sha256": canonical_hash(post_result),
        },
        "sha256": None,
    }
    evidence["sha256"] = canonical_hash(evidence)
    evidence_locator = f"{prefix}/packaging_exact_copy_canon_evidence.json"
    evidence_file_sha = write_json(root, evidence_locator, evidence)
    return {
        "primary_locator": primary_locator,
        "primary_hash": primary["file_sha256"],
        "packaging_exact_copy_evidence_locator": evidence_locator,
        "packaging_exact_copy_evidence_hash": evidence_file_sha,
        "packaging_run_root_locator": run_root_locator,
        "exact_copy_bundle_locator": locks["exact_copy_bundle"]["locator"],
    }


def create_inputs(
    root: Path,
    profile_id: str,
    asset_key: str,
    approval_owner: str | None = None,
    approval_status: str = "user_granted",
    authority_mode: str | None = None,
    input_tag: str | None = None,
) -> dict[str, Any]:
    profile = OWNER_PROFILES[profile_id]
    selected_authority_mode = authority_mode or profile.authority_modes[0][0]
    authority_roles = profile.roles_for_mode(selected_authority_mode)
    if authority_roles is None:
        raise AssertionError(f"test selected invalid authority mode {selected_authority_mode}")
    prefix = f"inputs/{profile_id}/{input_tag or asset_key}"
    exact_context: dict[str, str] = {}
    if (
        profile_id == "packaging_product"
        and selected_authority_mode == "geometry_layout_exact_copy_verified"
    ):
        exact_context = create_packaging_exact_copy_run_and_evidence(
            root, prefix, asset_key
        )
        primary_locator = exact_context["primary_locator"]
        primary_hash = exact_context["primary_hash"]
    else:
        primary_locator = f"{prefix}/primary.png"
        primary_hash = write_bytes(root, primary_locator, make_png())
    prompt_specs: list[tuple[str, str, str]] = []
    prompt_hashes: dict[str, str] = {}
    for role in profile.required_prompt_roles:
        locator = f"{prefix}/{role}.txt"
        digest = write_bytes(root, locator, f"{role} for {profile_id} {asset_key}\n".encode())
        prompt_specs.append((role, locator, digest))
        prompt_hashes[role] = digest
    approval = {
        "schema_version": "ai-video-owner-asset-approval.v1",
        "approval_event_id": f"APPROVE_{profile_id}_{asset_key}",
        "owner_skill": approval_owner or profile.owner_skill,
        "asset_key": asset_key,
        "primary_asset_sha256": primary_hash,
        "prompt_evidence_sha256": prompt_hashes,
        "affected_shot_uids": ["S001"],
        "authority_mode": selected_authority_mode,
        "control_roles_authorized": list(authority_roles),
        "authority_stage": profile.authority_stage,
        "terminal_route_decision": profile.terminal_route_decision,
        "assistant_qa_status": "passed",
        "production_approval_status": approval_status,
    }
    approval_locator = f"{prefix}/approval.json"
    approval_hash = write_json(root, approval_locator, approval)
    values = {
        "primary_locator": primary_locator,
        "primary_hash": primary_hash,
        "prompt_specs": prompt_specs,
        "approval_locator": approval_locator,
        "approval_hash": approval_hash,
        "authority_mode": selected_authority_mode,
    }
    values.update(exact_context)
    return values


def command(
    root: Path,
    profile_id: str,
    asset_key: str,
    values: dict[str, Any],
    version: str = "1.0.0",
    casting_as_terminal: bool = True,
) -> list[str]:
    cmd = [
        sys.executable,
        str(WRAPPERS[profile_id]),
        "--project-root", str(root),
        "--package-root", str(root / "exports" / f"{profile_id}-{asset_key}-v{version.replace('.', '_')}"),
        "--asset-key", asset_key,
        "--version", version,
        "--authority-mode", values["authority_mode"],
        "--primary-asset", values["primary_locator"],
        "--primary-asset-sha256", values["primary_hash"],
    ]
    for role, locator, digest in values["prompt_specs"]:
        cmd += ["--prompt-evidence", f"{role}={locator}={digest}"]
    cmd += [
        "--approval-evidence", values["approval_locator"],
        "--approval-evidence-sha256", values["approval_hash"],
        "--affected-shot-uid", "S001",
    ]
    if "packaging_exact_copy_evidence_locator" in values:
        cmd += [
            "--packaging-exact-copy-evidence",
            (
                f"{values['packaging_exact_copy_evidence_locator']}="
                f"{values['packaging_exact_copy_evidence_hash']}"
            ),
        ]
    if profile_id == "character_casting" and casting_as_terminal:
        cmd.append("--casting-as-terminal")
    return cmd


def run(
    cmd: list[str], extra_env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env.update(extra_env or {})
    return subprocess.run(
        cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        env=env, timeout=60, check=False,
    )


def expect_failure_without_manifest_mutation(
    root: Path, label: str, cmd: list[str], expected_text: str | None = None
) -> None:
    manifest_path = root / "00_project_canon/PROJECT_CANON_MANIFEST.json"
    before = manifest_path.read_bytes()
    result = run(cmd)
    if result.returncode == 0:
        raise AssertionError(f"{label} unexpectedly succeeded: {result.stdout}")
    if expected_text and expected_text.lower() not in result.stdout.lower():
        raise AssertionError(f"{label} did not report {expected_text!r}: {result.stdout}")
    if manifest_path.read_bytes() != before:
        raise AssertionError(f"{label} mutated PROJECT_CANON_MANIFEST on failure")


def add_consumer_chain(root: Path, producer_entry: dict[str, Any]) -> None:
    """Add a valid direct and transitive approved consumer chain to the fixture."""
    manifest_path = root / "00_project_canon/PROJECT_CANON_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    def consumer(
        artifact_id: str,
        owner: str,
        slot: str,
        producer: dict[str, Any],
    ) -> dict[str, Any]:
        dependency = {
            "artifact_id": producer["artifact_id"],
            "owner_skill": producer["owner_skill"],
            "version": producer["version"],
            "sha256": producer["sha256"],
        }
        record: dict[str, Any] = {
            "contract_version": "ai-video-artifact-v1",
            "artifact_id": artifact_id,
            "owner_skill": owner,
            "version": "1.0.0",
            "sha256": None,
            "approval_status": "user_approved",
            "dependencies": [dependency],
            "affected_shot_uids": ["S001"],
            "stale_reason": None,
        }
        record["sha256"] = canonical_hash(record)
        locator = f"artifacts/{artifact_id}.json"
        record_file_hash = write_json(root, locator, record)
        entry = {
            "artifact_slot": slot,
            "artifact_id": artifact_id,
            "artifact_type": slot.upper(),
            "owner_skill": owner,
            "version": "1.0.0",
            "sha256": record["sha256"],
            "approval_status": "user_approved",
            "stale_reason": None,
            "eligible_for_downstream": True,
            "affected_shot_uids": ["S001"],
            "locator": locator,
            "file_sha256": record_file_hash,
            "artifact_record_locator": locator,
            "artifact_record_file_sha256": record_file_hash,
            "dependencies": [dependency],
        }
        manifest["active_artifacts"].append(entry)
        manifest["dependency_edges"].append({
            "producer_artifact_id": producer["artifact_id"],
            "consumer_artifact_id": artifact_id,
            "producer_sha256": producer["sha256"],
            "affected_shot_uids": ["S001"],
        })
        return entry

    direct = consumer(
        "CONSUMER_DIRECT", "ai-video-global-look-lock", "synthetic_direct_consumer", producer_entry
    )
    consumer(
        "CONSUMER_TRANSITIVE", "ai-video-modular-storyboard", "synthetic_transitive_consumer", direct
    )
    major, minor, patch = (int(part) for part in manifest["version"].split("."))
    manifest["version"] = f"{major}.{minor}.{patch + 1}"
    manifest["revision_counter"] += 1
    manifest["updated_by_skill"] = "ai-video-shot-script-director"
    manifest["base_manifest_sha256"] = manifest["sha256"]
    manifest["sha256"] = None
    manifest["sha256"] = canonical_hash(manifest)
    write_json(root, "00_project_canon/PROJECT_CANON_MANIFEST.json", manifest)
    errors = validate_manifest(manifest) + verify_artifact_files(manifest, root)
    if errors:
        raise AssertionError(f"consumer-chain fixture invalid: {errors}")


def main() -> int:
    for unsafe_locator in (r"exports\asset.json", r"D:\asset.json", "/asset.json", "../asset.json"):
        if _safe_locator(unsafe_locator):
            raise AssertionError(f"non-portable asset locator was accepted: {unsafe_locator}")
    original_import = builtins.__import__

    def import_without_pillow(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "PIL" or name.startswith("PIL."):
            raise ImportError("synthetic missing Pillow")
        return original_import(name, *args, **kwargs)

    builtins.__import__ = import_without_pillow
    try:
        try:
            _image_metadata(make_png(), "primary.png")
        except ExportError as exc:
            if "Pillow is required" not in str(exc):
                raise AssertionError(f"missing Pillow failed for the wrong reason: {exc}")
        else:
            raise AssertionError("missing Pillow did not fail closed")
    finally:
        builtins.__import__ = original_import

    # Character lifecycle is a mutually exclusive terminal route. Casting is
    # pre-Canon unless the caller makes the one explicit terminal selection;
    # final and single-face are alternative terminal owners of the same slot.
    with tempfile.TemporaryDirectory(prefix="character-route-casting-") as temp:
        route_root = Path(temp)
        initialize_project(route_root)
        casting_values = create_inputs(route_root, "character_casting", "hero")
        expect_failure_without_manifest_mutation(
            route_root,
            "pre-Canon casting",
            command(
                route_root, "character_casting", "hero", casting_values,
                casting_as_terminal=False,
            ),
            "pre-Canon by default",
        )
        casting_result = run(command(route_root, "character_casting", "hero", casting_values))
        if casting_result.returncode != 0:
            raise AssertionError(f"explicit terminal casting failed: {casting_result.stdout}")
        final_values = create_inputs(route_root, "character_final", "hero")
        expect_failure_without_manifest_mutation(
            route_root,
            "terminal casting then final collision",
            command(route_root, "character_final", "hero", final_values),
            "cannot replace another owner's artifact slot",
        )

    with tempfile.TemporaryDirectory(prefix="character-route-final-") as temp:
        route_root = Path(temp)
        initialize_project(route_root)
        final_values = create_inputs(route_root, "character_final", "hero")
        final_result = run(command(route_root, "character_final", "hero", final_values))
        if final_result.returncode != 0:
            raise AssertionError(f"final route without casting export failed: {final_result.stdout}")
        single_values = create_inputs(route_root, "single_face_character", "hero")
        expect_failure_without_manifest_mutation(
            route_root,
            "final versus single-face collision",
            command(route_root, "single_face_character", "hero", single_values),
            "cannot replace another owner's artifact slot",
        )

    with tempfile.TemporaryDirectory(prefix="asset-canon-bridge-") as temp:
        root = Path(temp)
        initialize_project(root)

        positive_records: list[Path] = []
        for index, profile_id in enumerate(OWNER_PROFILES, start=1):
            asset_key = f"asset{index}"
            values = create_inputs(root, profile_id, asset_key)
            result = run(command(root, profile_id, asset_key, values))
            if result.returncode != 0:
                raise AssertionError(f"{profile_id} positive export failed: {result.stdout}")
            payload = json.loads(result.stdout.strip().splitlines()[-1])
            if payload.get("owner_skill") != OWNER_PROFILES[profile_id].owner_skill:
                raise AssertionError(f"{profile_id} returned wrong owner: {payload}")
            record_path = root / payload["artifact_record_locator"]
            record = json.loads(record_path.read_text(encoding="utf-8"))
            if (
                record.get("authority_stage") != OWNER_PROFILES[profile_id].authority_stage
                or record.get("terminal_route_decision")
                != OWNER_PROFILES[profile_id].terminal_route_decision
            ):
                raise AssertionError(f"{profile_id} lifecycle authority fields drifted: {record}")
            errors = validate_export_record(record, root)
            if errors:
                raise AssertionError(f"{profile_id} generated invalid record: {errors}")
            validator_result = run([
                sys.executable,
                str(EXPORT_VALIDATOR),
                str(record_path),
                "--project-root", str(root),
                "--canonical-manifest", str(root / "00_project_canon/PROJECT_CANON_MANIFEST.json"),
            ])
            if validator_result.returncode != 0:
                raise AssertionError(
                    f"{profile_id} standalone export validator failed: {validator_result.stdout}"
                )
            positive_records.append(record_path)

        manifest_path = root / "00_project_canon/PROJECT_CANON_MANIFEST.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        errors = validate_manifest(manifest) + verify_artifact_files(manifest, root)
        if errors:
            raise AssertionError(f"seven-owner durable Canon invalid: {errors}")
        actual_owners = {
            entry["owner_skill"] for entry in manifest["active_artifacts"]
            if entry["artifact_slot"] != "professional_shot_contract"
        }
        expected_owners = {profile.owner_skill for profile in OWNER_PROFILES.values()}
        if actual_owners != expected_owners:
            raise AssertionError(f"seven fixed owners not preserved: {actual_owners}")

        packaging_record = next(
            json.loads(path.read_text(encoding="utf-8"))
            for path in positive_records
            if json.loads(path.read_text(encoding="utf-8"))["owner_skill"]
            == "packaging-product-identity-label-lock-board"
        )
        if packaging_record["control_roles_authorized"] != ["product_geometry"]:
            raise AssertionError("ordinary packaging export was incorrectly granted label_copy authority")
        escalated = copy.deepcopy(packaging_record)
        escalated["control_roles_authorized"] = ["product_geometry", "label_copy"]
        escalated["sha256"] = canonical_hash(escalated)
        escalation_errors = validate_export_record(escalated, root)
        if not any("capability set" in error for error in escalation_errors):
            raise AssertionError(f"self-declared label_copy escalation was accepted: {escalation_errors}")

        exact_values = create_inputs(
            root,
            "packaging_product",
            "exactpack",
            authority_mode="geometry_layout_exact_copy_verified",
        )
        exact_command = command(root, "packaging_product", "exactpack", exact_values)
        missing_evidence = list(exact_command)
        exact_flag_index = missing_evidence.index("--packaging-exact-copy-evidence")
        del missing_evidence[exact_flag_index:exact_flag_index + 2]
        expect_failure_without_manifest_mutation(
            root,
            "exact packaging without authority evidence",
            missing_evidence,
            "requires --packaging-exact-copy-evidence",
        )
        legacy_v1 = {
            "schema_version": "packaging-exact-copy-canon-evidence.v1",
            "owner_skill": "packaging-product-identity-label-lock-board",
            "asset_key": "exactpack",
            "primary_asset_sha256": exact_values["primary_hash"],
            "exact_copy_bundle": {}, "coverage_matrix": {},
            "generation_prompt_index": {}, "post_composite_verification": {},
            "lock_statuses": {}, "assistant_qa_status": "passed", "sha256": None,
        }
        legacy_v1["sha256"] = canonical_hash(legacy_v1)
        legacy_locator = "inputs/packaging_product/exactpack/legacy_v1_evidence.json"
        legacy_hash = write_json(root, legacy_locator, legacy_v1)
        legacy_command = list(exact_command)
        legacy_command[legacy_command.index("--packaging-exact-copy-evidence") + 1] = (
            f"{legacy_locator}={legacy_hash}"
        )
        expect_failure_without_manifest_mutation(
            root, "legacy v1 exact-copy evidence", legacy_command, "schema_version"
        )

        arbitrary_locator = "inputs/packaging_product/exactpack/arbitrary.png"
        arbitrary_hash = write_bytes(root, arbitrary_locator, make_png())
        arbitrary_command = list(exact_command)
        arbitrary_command[arbitrary_command.index("--primary-asset") + 1] = arbitrary_locator
        arbitrary_command[arbitrary_command.index("--primary-asset-sha256") + 1] = arbitrary_hash
        expect_failure_without_manifest_mutation(
            root,
            "exact packaging arbitrary non-member primary",
            arbitrary_command,
            "primary_asset_sha256 mismatch",
        )
        exact_bundle = root / exact_values["exact_copy_bundle_locator"]
        exact_bundle_bytes = exact_bundle.read_bytes()
        exact_bundle.write_bytes(exact_bundle_bytes + b"\n")
        expect_failure_without_manifest_mutation(
            root,
            "exact packaging with drifted bundle",
            exact_command,
            "sha-256 mismatch",
        )
        exact_bundle.write_bytes(exact_bundle_bytes)
        exact_result = run(exact_command)
        if exact_result.returncode != 0:
            raise AssertionError(f"exact-copy-verified packaging export failed: {exact_result.stdout}")
        exact_payload = json.loads(exact_result.stdout.strip().splitlines()[-1])
        exact_record = json.loads((root / exact_payload["artifact_record_locator"]).read_text(encoding="utf-8"))
        if exact_record["control_roles_authorized"] != ["product_geometry", "label_copy"]:
            raise AssertionError("exact-copy-verified packaging export did not lock label_copy authority")
        if exact_record.get("authority_evidence", {}).get("role") != "packaging_exact_copy":
            raise AssertionError("exact-copy packaging export did not bind authority evidence")

        # Wrapper CLI has no owner field, so an attempted owner override is rejected.
        values = create_inputs(root, "character_final", "spoofcli")
        spoof_cli = command(root, "character_final", "spoofcli", values) + ["--owner-skill", "banana-owner"]
        expect_failure_without_manifest_mutation(root, "owner override CLI", spoof_cli, "unrecognized arguments")

        # An owner-spoofed explicit approval is independently rejected.
        values = create_inputs(root, "character_final", "spoofrecord", approval_owner="banana-owner")
        expect_failure_without_manifest_mutation(
            root, "approval owner spoof", command(root, "character_final", "spoofrecord", values), "fixed owner"
        )

        values = create_inputs(root, "single_face_character", "route-spoof")
        approval_value = json.loads((root / values["approval_locator"]).read_text(encoding="utf-8"))
        approval_value["terminal_route_decision"] = "character_final"
        values["approval_hash"] = write_json(root, values["approval_locator"], approval_value)
        expect_failure_without_manifest_mutation(
            root,
            "approval terminal route spoof",
            command(root, "single_face_character", "route-spoof", values),
            "terminal_route_decision mismatch",
        )

        # Rehashing a tampered record cannot turn a mismatched profile/owner into authority.
        original_record = json.loads(positive_records[0].read_text(encoding="utf-8"))
        tampered = copy.deepcopy(original_record)
        tampered["owner_skill"] = "character-final-lock-board"
        tampered["sha256"] = canonical_hash(tampered)
        tamper_errors = validate_export_record(tampered, root)
        if not any("fixed profile" in error for error in tamper_errors):
            raise AssertionError(f"rehash owner spoof was not rejected: {tamper_errors}")

        values = create_inputs(root, "multi_angle_product", "traversal")
        traversal_cmd = command(root, "multi_angle_product", "traversal", values)
        traversal_cmd[traversal_cmd.index("--primary-asset") + 1] = "../outside.bin"
        expect_failure_without_manifest_mutation(root, "path traversal", traversal_cmd, "safe project-relative")

        values = create_inputs(root, "packaging_product", "badhash")
        bad_primary = command(root, "packaging_product", "badhash", values)
        bad_primary[bad_primary.index("--primary-asset-sha256") + 1] = "0" * 64
        expect_failure_without_manifest_mutation(root, "primary hash mismatch", bad_primary, "sha-256 mismatch")

        values = create_inputs(root, "multi_angle_product", "notanimage")
        blob_hash = write_bytes(root, values["primary_locator"], b"arbitrary non-image bytes")
        approval_value = json.loads((root / values["approval_locator"]).read_text(encoding="utf-8"))
        approval_value["primary_asset_sha256"] = blob_hash
        values["primary_hash"] = blob_hash
        values["approval_hash"] = write_json(root, values["approval_locator"], approval_value)
        expect_failure_without_manifest_mutation(
            root,
            "arbitrary binary primary",
            command(root, "multi_angle_product", "notanimage", values),
            "png, jpeg, or webp",
        )

        values = create_inputs(root, "scene_canon", "forgedpng")
        forged_hash = write_bytes(root, values["primary_locator"], make_forged_header_png())
        approval_value = json.loads((root / values["approval_locator"]).read_text(encoding="utf-8"))
        approval_value["primary_asset_sha256"] = forged_hash
        values["primary_hash"] = forged_hash
        values["approval_hash"] = write_json(root, values["approval_locator"], approval_value)
        expect_failure_without_manifest_mutation(
            root,
            "forged image header",
            command(root, "scene_canon", "forgedpng", values),
            "fully decodable",
        )

        values = create_inputs(root, "material_sensitive_product", "badprompt")
        bad_prompt = command(root, "material_sensitive_product", "badprompt", values)
        prompt_index = bad_prompt.index("--prompt-evidence") + 1
        role, locator, _ = bad_prompt[prompt_index].split("=", 2)
        bad_prompt[prompt_index] = f"{role}={locator}={'0' * 64}"
        expect_failure_without_manifest_mutation(root, "prompt hash mismatch", bad_prompt, "sha-256 mismatch")

        values = create_inputs(root, "scene_canon", "unapproved", approval_status="not_granted")
        expect_failure_without_manifest_mutation(
            root, "unapproved asset", command(root, "scene_canon", "unapproved", values), "production approval"
        )

        # Four-lock drift is detected against actual primary bytes.
        primary_entry = next(
            entry for entry in manifest["active_artifacts"]
            if entry["owner_skill"] == "character-casting-lock-board"
        )
        primary_path = root / primary_entry["locator"]
        original_bytes = primary_path.read_bytes()
        primary_path.write_bytes(original_bytes + b"drift")
        drift_errors = verify_artifact_files(manifest, root)
        if not any("file_sha256 mismatch" in error for error in drift_errors):
            raise AssertionError(f"primary byte drift was not detected: {drift_errors}")
        primary_path.write_bytes(original_bytes)

        # Replacing an asset atomically stales the complete downstream closure,
        # while the immutable consumer records remain approved and four-locked.
        current_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        old_casting = next(
            entry for entry in current_manifest["active_artifacts"]
            if entry["owner_skill"] == "character-casting-lock-board"
        )
        add_consumer_chain(root, old_casting)
        replacement_inputs = create_inputs(
            root, "character_casting", "asset1", input_tag="asset1-v2"
        )
        replacement = run(command(
            root, "character_casting", "asset1", replacement_inputs, version="2.0.0"
        ))
        if replacement.returncode != 0:
            raise AssertionError(f"replacement with consumer closure failed: {replacement.stdout}")
        replacement_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        replacement_errors = validate_manifest(replacement_manifest) + verify_artifact_files(replacement_manifest, root)
        if replacement_errors:
            raise AssertionError(f"replacement durable Canon invalid: {replacement_errors}")
        overlay_ids = {"CONSUMER_DIRECT", "CONSUMER_TRANSITIVE"}
        by_id = {entry["artifact_id"]: entry for entry in replacement_manifest["active_artifacts"]}
        for consumer_id in overlay_ids:
            entry = by_id[consumer_id]
            if entry["approval_status"] != "stale" or entry["eligible_for_downstream"] is not False:
                raise AssertionError(f"{consumer_id} was not stale-overlaid")
            owner_record = json.loads((root / entry["artifact_record_locator"]).read_text(encoding="utf-8"))
            if owner_record["approval_status"] != "user_approved" or owner_record["stale_reason"] is not None:
                raise AssertionError(f"{consumer_id} immutable owner record was rewritten")
        old_history = next(
            entry for entry in replacement_manifest["superseded_artifacts"]
            if entry["artifact_id"] == old_casting["artifact_id"]
        )
        if old_history["eligible_for_downstream"] is not False:
            raise AssertionError("superseded asset stayed downstream-eligible")

        missing_event = copy.deepcopy(replacement_manifest)
        missing_event["stale_events"] = [
            event for event in missing_event["stale_events"]
            if "CONSUMER_DIRECT" not in event["stale_artifact_ids"]
        ]
        missing_event["sha256"] = None
        missing_event["sha256"] = canonical_hash(missing_event)
        missing_event_errors = validate_manifest(missing_event) + verify_artifact_files(missing_event, root)
        if not any("stale_event" in error or "stale overlay" in error for error in missing_event_errors):
            raise AssertionError(f"missing replacement event was not rejected: {missing_event_errors}")

        still_eligible = copy.deepcopy(replacement_manifest)
        still_eligible_entry = next(
            entry for entry in still_eligible["active_artifacts"]
            if entry["artifact_id"] == "CONSUMER_DIRECT"
        )
        still_eligible_entry.update({
            "approval_status": "user_approved", "stale_reason": None, "eligible_for_downstream": True,
        })
        still_eligible["sha256"] = None
        still_eligible["sha256"] = canonical_hash(still_eligible)
        eligible_errors = validate_manifest(still_eligible) + verify_artifact_files(still_eligible, root)
        if not any("superseded dependency" in error or "only while stale/blocked" in error for error in eligible_errors):
            raise AssertionError(f"eligible historical consumer was not rejected: {eligible_errors}")

        # Fixed wrapper/profile location is also enforced at runtime.
        sys.path.insert(0, str(SKILL_ROOT / "ai-video-shot-script-director/scripts"))
        from build_asset_canon_export import run_fixed_owner_cli
        captured = io.StringIO()
        with contextlib.redirect_stdout(captured):
            mismatch_code = run_fixed_owner_cli("character_casting", WRAPPERS["character_final"], [])
        if mismatch_code == 0:
            raise AssertionError("wrapper path/profile mismatch unexpectedly succeeded")

    # Fault injection proves an applied receipt cannot precede Canon.  The
    # identical rerun reconstructs the receipt from immutable base/delta/record.
    with tempfile.TemporaryDirectory(prefix="asset-canon-crash-") as temp:
        crash_root = Path(temp)
        initialize_project(crash_root)
        crash_values = create_inputs(crash_root, "character_final", "crashsafe")
        crash_cmd = command(crash_root, "character_final", "crashsafe", crash_values)
        faulted = run(
            crash_cmd,
            {"AI_VIDEO_CANON_TEST_FAULT_AFTER_MANIFEST_REPLACE": "1"},
        )
        if faulted.returncode == 0 or "fault injected" not in faulted.stdout:
            raise AssertionError(f"fault injection did not stop after Canon replace: {faulted.stdout}")
        crash_package = crash_root / "exports/character_final-crashsafe-v1_0_0/00_manifest"
        if (crash_package / "MANIFEST_UPDATE_RECEIPT.json").exists():
            raise AssertionError("false-applied receipt existed before durable recovery")
        crash_manifest = json.loads(
            (crash_root / "00_project_canon/PROJECT_CANON_MANIFEST.json").read_text(encoding="utf-8")
        )
        if not any(
            entry.get("owner_skill") == "character-final-lock-board"
            for entry in crash_manifest.get("active_artifacts", [])
            if isinstance(entry, dict)
        ):
            raise AssertionError("fault was not injected after the Canon commit")
        recovered = run(crash_cmd)
        if recovered.returncode != 0:
            raise AssertionError(f"committed transition receipt recovery failed: {recovered.stdout}")
        recovered_payload = json.loads(recovered.stdout.strip().splitlines()[-1])
        if recovered_payload.get("status") not in {"recovered_applied_receipt", "already_applied"}:
            raise AssertionError(f"rerun did not report receipt recovery: {recovered_payload}")
        if not (crash_package / "MANIFEST_UPDATE_RECEIPT.json").is_file():
            raise AssertionError("recovery did not publish the applied receipt")

    for fault_var, label in (
        ("AI_VIDEO_CANON_TEST_FAULT_AFTER_BASE_DELTA", "base-delta"),
        ("AI_VIDEO_CANON_TEST_FAULT_AFTER_RECORD", "owner-record"),
    ):
        with tempfile.TemporaryDirectory(prefix=f"asset-canon-precommit-{label}-") as temp:
            resume_root = Path(temp)
            initialize_project(resume_root)
            resume_values = create_inputs(resume_root, "scene_canon", f"resume{label.replace('-', '')}")
            resume_cmd = command(
                resume_root, "scene_canon", f"resume{label.replace('-', '')}", resume_values
            )
            manifest_path = resume_root / "00_project_canon/PROJECT_CANON_MANIFEST.json"
            before = manifest_path.read_bytes()
            faulted = run(resume_cmd, {fault_var: "1"})
            if faulted.returncode == 0 or "fault injected" not in faulted.stdout:
                raise AssertionError(f"{label} fault injection did not stop preparation: {faulted.stdout}")
            if manifest_path.read_bytes() != before:
                raise AssertionError(f"{label} precommit fault mutated Canon")
            package = resume_root / (
                f"exports/scene_canon-resume{label.replace('-', '')}-v1_0_0/00_manifest"
            )
            if (package / "MANIFEST_UPDATE_RECEIPT.json").exists():
                raise AssertionError(f"{label} precommit fault created a false applied receipt")
            if label == "base-delta":
                other_values = create_inputs(resume_root, "character_final", "blockedother")
                other_cmd = command(
                    resume_root, "character_final", "blockedother", other_values
                )
                blocked = run(other_cmd)
                if blocked.returncode == 0 or "another prepared Canon transaction" not in blocked.stdout:
                    raise AssertionError(
                        f"unrelated writer was not blocked by prepared transaction journal: {blocked.stdout}"
                    )
                if manifest_path.read_bytes() != before:
                    raise AssertionError("blocked unrelated writer mutated Canon")
            resumed = run(resume_cmd)
            if resumed.returncode != 0:
                raise AssertionError(f"{label} exact-byte resume failed: {resumed.stdout}")
            if not (package / "MANIFEST_UPDATE_RECEIPT.json").is_file():
                raise AssertionError(f"{label} resume did not finish the applied receipt")

    # A later writer must first recover a prior committed/no-receipt journal,
    # then build on that recovered post. This closes the A-fault -> B-commit
    # history window without scanning arbitrary package directories.
    with tempfile.TemporaryDirectory(prefix="asset-canon-journal-chain-") as temp:
        chain_root = Path(temp)
        initialize_project(chain_root)
        first_values = create_inputs(chain_root, "character_casting", "journalA")
        first_cmd = command(chain_root, "character_casting", "journalA", first_values)
        first_fault = run(
            first_cmd, {"AI_VIDEO_CANON_TEST_FAULT_AFTER_MANIFEST_REPLACE": "1"}
        )
        if first_fault.returncode == 0:
            raise AssertionError("journal chain first transaction did not fault")
        first_receipt = chain_root / "exports/character_casting-journalA-v1_0_0/00_manifest/MANIFEST_UPDATE_RECEIPT.json"
        if first_receipt.exists():
            raise AssertionError("journal chain first transaction wrote a false receipt")
        second_values = create_inputs(chain_root, "scene_canon", "journalB")
        second_cmd = command(chain_root, "scene_canon", "journalB", second_values)
        second_result = run(second_cmd)
        if second_result.returncode != 0:
            raise AssertionError(f"later writer failed to recover prior transaction: {second_result.stdout}")
        if not first_receipt.is_file():
            raise AssertionError("later writer did not recover the first applied receipt")
        if (chain_root / "00_project_canon/PENDING_PROJECT_CANON_TRANSACTION.json").exists():
            raise AssertionError("pending transaction journal survived completed recovery/commit")
        chain_manifest = json.loads(
            (chain_root / "00_project_canon/PROJECT_CANON_MANIFEST.json").read_text(encoding="utf-8")
        )
        chain_owners = {
            item["owner_skill"] for item in chain_manifest["active_artifacts"]
            if item["owner_skill"] in {"character-casting-lock-board", "scene-canon-asset-pack"}
        }
        if chain_owners != {"character-casting-lock-board", "scene-canon-asset-pack"}:
            raise AssertionError(f"journal chain lost one committed asset: {chain_owners}")

    # Two concurrent fixed-owner exports serialize across read/candidate/CAS/
    # replace/readback.  Both may commit, but the second must build on the first
    # rather than silently overwriting it.
    with tempfile.TemporaryDirectory(prefix="asset-canon-concurrency-") as temp:
        concurrent_root = Path(temp)
        initialize_project(concurrent_root)
        values_a = create_inputs(concurrent_root, "character_casting", "parallelA")
        values_b = create_inputs(concurrent_root, "multi_angle_product", "parallelB")
        cmd_a = command(concurrent_root, "character_casting", "parallelA", values_a)
        cmd_b = command(concurrent_root, "multi_angle_product", "parallelB", values_b)
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        proc_a = subprocess.Popen(
            cmd_a, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env
        )
        proc_b = subprocess.Popen(
            cmd_b, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env
        )
        out_a, _ = proc_a.communicate(timeout=60)
        out_b, _ = proc_b.communicate(timeout=60)
        if proc_a.returncode != 0 or proc_b.returncode != 0:
            raise AssertionError(
                f"serialized concurrent exports failed: A={proc_a.returncode} {out_a}; "
                f"B={proc_b.returncode} {out_b}"
            )
        concurrent_manifest = json.loads(
            (concurrent_root / "00_project_canon/PROJECT_CANON_MANIFEST.json").read_text(encoding="utf-8")
        )
        parallel_owners = {
            entry["owner_skill"] for entry in concurrent_manifest["active_artifacts"]
            if entry["owner_skill"] in {
                "character-casting-lock-board", "multi-angle-product-identity-lock-board"
            }
        }
        if parallel_owners != {
            "character-casting-lock-board", "multi-angle-product-identity-lock-board"
        }:
            raise AssertionError(f"concurrent lost-update detected: {parallel_owners}")
        concurrency_errors = validate_manifest(concurrent_manifest) + verify_artifact_files(
            concurrent_manifest, concurrent_root
        )
        if concurrency_errors:
            raise AssertionError(f"concurrent durable Canon invalid: {concurrency_errors}")

    print("OK: seven fixed-owner asset Canon bridges passed positive and adversarial tests")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
