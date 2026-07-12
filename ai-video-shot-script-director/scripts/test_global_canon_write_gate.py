#!/usr/bin/env python3
"""Cross-writer tests for the shared global Project Canon write gate."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from test_asset_canon_bridge import command as asset_command
from test_asset_canon_bridge import create_inputs, initialize_project, run as run_asset
from validate_project_canon_manifest import canonical_hash, validate_manifest, verify_artifact_files


ROOT = Path(__file__).resolve().parents[2]
WRITERS = {
    "ai-video-shot-script-director": ROOT / "ai-video-shot-script-director/scripts/apply_project_canon_transition.py",
    "ai-video-global-look-lock": ROOT / "ai-video-global-look-lock/scripts/apply_project_canon_transition.py",
    "ai-video-modular-storyboard": ROOT / "ai-video-modular-storyboard/scripts/apply_project_canon_transition.py",
    "ai-video-timed-animatic-previs-director": ROOT / "ai-video-timed-animatic-previs-director/scripts/apply_project_canon_transition.py",
    "ai-video-keyframe-continuity-pack": ROOT / "ai-video-keyframe-continuity-pack/scripts/apply_project_canon_transition.py",
    "ai-video-omni-reference-prompt-director": ROOT / "ai-video-omni-reference-prompt-director/scripts/apply_project_canon_transition.py",
}
PHASE = {
    "ai-video-shot-script-director": "professional_script",
    "ai-video-global-look-lock": "global_look",
    "ai-video-modular-storyboard": "storyboard_final",
    "ai-video-timed-animatic-previs-director": "control_previs_v2",
    "ai-video-keyframe-continuity-pack": "core_keyframes_k1",
    "ai-video-omni-reference-prompt-director": "prompt_compile_p2",
}


def write_json(path: Path, value: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def next_version(value: str) -> str:
    major, minor, patch = (int(part) for part in value.split("."))
    return f"{major}.{minor}.{patch + 1}"


def prepare_workflow_transition(
    project: Path,
    owner: str,
    transaction_id: str,
    artifact_id: str,
) -> tuple[Path, list[str]]:
    manifest_path = project / "00_project_canon/PROJECT_CANON_MANIFEST.json"
    base_bytes = manifest_path.read_bytes()
    base = json.loads(base_bytes)
    record: dict[str, Any] = {
        "contract_version": "ai-video-artifact-v1",
        "artifact_id": artifact_id,
        "owner_skill": owner,
        "version": "1.0.0",
        "sha256": None,
        "approval_status": "assistant_validated",
        "dependencies": [],
        "affected_shot_uids": ["S001"],
        "stale_reason": None,
    }
    record["sha256"] = canonical_hash(record)
    record_locator = f"owned_artifacts/{artifact_id}.json"
    record_file_sha = write_json(project / record_locator, record)
    entry = {
        "artifact_slot": f"synthetic_workflow:{artifact_id.lower()}",
        "artifact_id": artifact_id,
        "artifact_type": "SYNTHETIC_WORKFLOW_ARTIFACT",
        "owner_skill": owner,
        "version": "1.0.0",
        "sha256": record["sha256"],
        "approval_status": "assistant_validated",
        "stale_reason": None,
        "eligible_for_downstream": True,
        "affected_shot_uids": ["S001"],
        "locator": record_locator,
        "file_sha256": record_file_sha,
        "artifact_record_locator": record_locator,
        "artifact_record_file_sha256": record_file_sha,
        "dependencies": [],
    }
    candidate = copy.deepcopy(base)
    candidate["active_artifacts"].append(entry)
    candidate["active_artifacts"].sort(key=lambda item: item["artifact_slot"])
    candidate.update({
        "version": next_version(base["version"]),
        "sha256": None,
        "current_phase": PHASE[owner],
        "revision_counter": base["revision_counter"] + 1,
        "updated_by_skill": owner,
        "base_manifest_sha256": base["sha256"],
    })
    candidate["sha256"] = canonical_hash(candidate)
    package = project / f"workflow_packages/{transaction_id}"
    manifest_dir = package / "00_manifest"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    (manifest_dir / "BASE_PROJECT_CANON_SNAPSHOT.json").write_bytes(base_bytes)
    write_json(manifest_dir / "CANDIDATE_PROJECT_CANON_POST.json", candidate)
    return package, [artifact_id]


def writer_command(
    project: Path,
    package: Path,
    owner: str,
    transaction_id: str,
    registered: list[str],
) -> list[str]:
    command = [
        sys.executable, str(WRITERS[owner]),
        "--project-root", str(project),
        "--package-root", str(package),
        "--transaction-id", transaction_id,
    ]
    for artifact_id in registered:
        command += ["--expected-registered-artifact-id", artifact_id]
    return command


def run(command: list[str], fault: str | None = None) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    if fault:
        env[fault] = "1"
    return subprocess.run(
        command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        env=env, timeout=60, check=False,
    )


def main() -> int:
    # A prepared asset transaction blocks every other Canon writer.
    with tempfile.TemporaryDirectory(prefix="canon-gate-block-") as temp:
        project = Path(temp)
        initialize_project(project)
        asset_values = create_inputs(project, "character_final", "gateA")
        asset_cmd = asset_command(project, "character_final", "gateA", asset_values)
        before = (project / "00_project_canon/PROJECT_CANON_MANIFEST.json").read_bytes()
        faulted = run_asset(
            asset_cmd, {"AI_VIDEO_CANON_TEST_FAULT_AFTER_RECORD": "1"}
        )
        if faulted.returncode == 0:
            raise AssertionError("asset precommit fault did not leave a pending journal")
        for index, (owner, wrapper) in enumerate(WRITERS.items(), start=1):
            package = project / f"blocked/{index}"
            attempted = writer_command(project, package, owner, f"BLOCKED_{index}", [f"BLOCKED_{index}"])
            result = run(attempted)
            if result.returncode == 0 or "another prepared Canon transaction" not in result.stdout:
                raise AssertionError(f"{owner} crossed a prepared asset journal: {result.stdout}")
            if (project / "00_project_canon/PROJECT_CANON_MANIFEST.json").read_bytes() != before:
                raise AssertionError(f"{owner} mutated Canon while blocked")
        resumed = run_asset(asset_cmd)
        if resumed.returncode != 0:
            raise AssertionError(f"asset pending transaction could not resume: {resumed.stdout}")

    # A workflow writer recovers an asset postcommit receipt before advancing.
    with tempfile.TemporaryDirectory(prefix="canon-gate-asset-recovery-") as temp:
        project = Path(temp)
        initialize_project(project)
        asset_values = create_inputs(project, "scene_canon", "gateScene")
        asset_cmd = asset_command(project, "scene_canon", "gateScene", asset_values)
        faulted = run_asset(
            asset_cmd, {"AI_VIDEO_CANON_TEST_FAULT_AFTER_MANIFEST_REPLACE": "1"}
        )
        if faulted.returncode == 0:
            raise AssertionError("asset postcommit fault did not trigger")
        asset_receipt = project / "exports/scene_canon-gateScene-v1_0_0/00_manifest/MANIFEST_UPDATE_RECEIPT.json"
        if asset_receipt.exists():
            raise AssertionError("asset postcommit fault created a false receipt")
        package, registered = prepare_workflow_transition(
            project, "ai-video-global-look-lock", "LOOK_AFTER_ASSET", "LOOK_AFTER_ASSET_ARTIFACT"
        )
        result = run(writer_command(
            project, package, "ai-video-global-look-lock", "LOOK_AFTER_ASSET", registered
        ))
        if result.returncode != 0:
            raise AssertionError(f"Look failed to recover asset journal before commit: {result.stdout}")
        if not asset_receipt.is_file():
            raise AssertionError("Look did not reconstruct prior asset receipt")

    # A workflow postcommit fault is recovered by a different workflow writer.
    with tempfile.TemporaryDirectory(prefix="canon-gate-workflow-recovery-") as temp:
        project = Path(temp)
        initialize_project(project)
        look_package, look_ids = prepare_workflow_transition(
            project, "ai-video-global-look-lock", "LOOK_FAULT", "LOOK_FAULT_ARTIFACT"
        )
        look_cmd = writer_command(
            project, look_package, "ai-video-global-look-lock", "LOOK_FAULT", look_ids
        )
        faulted = run(look_cmd, "AI_VIDEO_CANON_TEST_FAULT_AFTER_MANIFEST_REPLACE")
        if faulted.returncode == 0:
            raise AssertionError("workflow postcommit fault did not trigger")
        look_receipt = look_package / "00_manifest/MANIFEST_UPDATE_RECEIPT.json"
        if look_receipt.exists():
            raise AssertionError("workflow fault created a false receipt")
        mismatched_ids = run(writer_command(
            project, look_package, "ai-video-global-look-lock", "LOOK_FAULT", ["FORGED_ID"]
        ))
        if mismatched_ids.returncode == 0 or "registered artifact IDs differ" not in mismatched_ids.stdout:
            raise AssertionError(
                f"same workflow transaction resumed with forged registered IDs: {mismatched_ids.stdout}"
            )
        mismatched_preserved_cmd = writer_command(
            project, look_package, "ai-video-global-look-lock", "LOOK_FAULT", look_ids
        ) + ["--preserved-artifact-id", "SHOT_CONTRACT_SYNTHETIC"]
        mismatched_preserved = run(mismatched_preserved_cmd)
        if (
            mismatched_preserved.returncode == 0
            or "preserved artifact IDs differ" not in mismatched_preserved.stdout
        ):
            raise AssertionError(
                "same workflow transaction resumed with forged preserved IDs: "
                + mismatched_preserved.stdout
            )
        if look_receipt.exists():
            raise AssertionError("mismatched workflow resume reconstructed a receipt")
        storyboard_package, storyboard_ids = prepare_workflow_transition(
            project, "ai-video-modular-storyboard", "STORY_AFTER_LOOK", "STORY_AFTER_LOOK_ARTIFACT"
        )
        result = run(writer_command(
            project, storyboard_package, "ai-video-modular-storyboard",
            "STORY_AFTER_LOOK", storyboard_ids,
        ))
        if result.returncode != 0:
            raise AssertionError(f"Storyboard failed to recover Look journal: {result.stdout}")
        if not look_receipt.is_file():
            raise AssertionError("Storyboard did not reconstruct Look receipt")
        manifest = json.loads(
            (project / "00_project_canon/PROJECT_CANON_MANIFEST.json").read_text(encoding="utf-8")
        )
        errors = validate_manifest(manifest) + verify_artifact_files(manifest, project)
        if errors:
            raise AssertionError(f"final cross-writer Canon invalid: {errors}")
        owners = {entry["owner_skill"] for entry in manifest["active_artifacts"]}
        if not {"ai-video-global-look-lock", "ai-video-modular-storyboard"} <= owners:
            raise AssertionError(f"workflow successor lost an artifact: {owners}")
        if (project / "00_project_canon/PENDING_PROJECT_CANON_TRANSACTION.json").exists():
            raise AssertionError("global journal survived completed workflow recovery")

    print("OK: all six workflow writers share the global Canon lock/journal gate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
