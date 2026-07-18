#!/usr/bin/env python3
"""Self-contained red/green tests for the standalone material board v5 chain."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Callable

from PIL import Image


SCRIPT_DIR = Path(__file__).resolve().parent
FREEZER = SCRIPT_DIR / "freeze_reference_bundle.py"
CONTRACT_FREEZER = SCRIPT_DIR / "freeze_material_source_contract.py"
EXEC_RENDERER = SCRIPT_DIR / "render_worker_exec.py"
SPAWN_FREEZER = SCRIPT_DIR / "freeze_worker_spawn.py"
ENHANCEMENT_RENDERER = SCRIPT_DIR / "render_4k_enhancement_prompt.py"
RESOLVER = SCRIPT_DIR / "resolve_worker_image.py"
FINAL_BUILDER = SCRIPT_DIR / "build_final_result.py"
INSPECTION_SCAFFOLDER = SCRIPT_DIR / "scaffold_board_inspection.py"
INSPECTION_FREEZER = SCRIPT_DIR / "freeze_board_inspection.py"
POST_GENERATION_FREEZER = SCRIPT_DIR / "freeze_post_generation_records.py"
sys.path.insert(0, str(SCRIPT_DIR))
from material_contract import (  # noqa: E402
    render_4k_enhancement_prompt_bytes,
    render_worker_exec_bytes,
)
from material_decision_records import (  # noqa: E402
    build_accepted_record,
    build_handoff_record,
    build_qa_record,
    fact_sources,
)


NONCE = "0123456789abcdef0123456789abcdef"
PARENT_ID = "019f0000-0000-7000-8000-000000000001"
THREAD_ID = "019f0000-0000-7000-8000-000000000002"
TURN_ID = "019f0000-0000-7000-8000-000000000003"
IMAGE_CALL_ID = "exec-11111111-2222-4333-8444-555555555555"
AGENT_PATH = "/" + "root/material-image-worker-v4-01234567"
CHECKPOINT = 1_750_000_000_000


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def write_events(path: Path, events: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(event, ensure_ascii=False) + "\n" for event in events),
        encoding="utf-8",
        newline="\n",
    )


def make_image(
    path: Path,
    *,
    color: tuple[int, int, int, int],
    size: tuple[int, int],
    image_format: str,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = "RGBA" if image_format == "PNG" else "RGB"
    image_color = color if mode == "RGBA" else color[:3]
    with Image.new(mode, size, image_color) as image:
        image.save(path, format=image_format)


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def error_code(result: subprocess.CompletedProcess[str]) -> str | None:
    for line in reversed(result.stderr.splitlines()):
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload.get("error_code")
    return None


def source_contract_draft() -> dict[str, Any]:
    return {
        "schema_version": "material_source_contract_draft.v1",
        "asset_id": "material-test-asset",
        "source_authority": [
            {
                "alias": "product_front",
                "authority": "authoritative_source",
                "allowed_uses": [
                    "identity",
                    "silhouette",
                    "proportions",
                    "topology",
                    "structure",
                    "panel_composition",
                ],
                "exclusions": ["hidden interior", "open state"],
            },
            {
                "alias": "material_macro",
                "authority": "supporting_source",
                "allowed_uses": ["material", "color", "panel_composition"],
                "exclusions": ["global silhouette", "hidden topology"],
            },
        ],
        "fact_registry": {
            "verified": [
                {
                    "fact_id": "identity_fact",
                    "statement": "The hero silhouette and proportions follow the product front source.",
                    "source_aliases": ["product_front"],
                },
                {
                    "fact_id": "topology_fact",
                    "statement": "The visible connector topology remains one continuous source-matched chain.",
                    "source_aliases": ["product_front"],
                },
                {
                    "fact_id": "structure_fact",
                    "statement": "The visible rim and body junction preserve their source relationship.",
                    "source_aliases": ["product_front"],
                },
                {
                    "fact_id": "material_fact",
                    "statement": "The translucent shell keeps the source highlight boundary and edge depth.",
                    "source_aliases": ["material_macro"],
                },
            ],
            "inferred": [
                {
                    "fact_id": "back_finish_inferred",
                    "statement": "The unseen rear finish may resemble the visible side but is not authoritative.",
                    "source_aliases": ["product_front"],
                }
            ],
            "needs_source": [
                {
                    "fact_id": "open_state_missing",
                    "statement": "The open state is not visible and must not be shown.",
                    "source_aliases": [],
                }
            ],
        },
        "critical_invariants": [
            {
                "invariant_id": "inv_identity",
                "category": "identity",
                "fact_id": "identity_fact",
                "required_for_acceptance": True,
            },
            {
                "invariant_id": "inv_topology",
                "category": "topology",
                "fact_id": "topology_fact",
                "required_for_acceptance": True,
            },
            {
                "invariant_id": "inv_structure",
                "category": "structure",
                "fact_id": "structure_fact",
                "required_for_acceptance": True,
            },
            {
                "invariant_id": "inv_material",
                "category": "material",
                "fact_id": "material_fact",
                "required_for_acceptance": True,
            },
        ],
        "panel_plan": [
            {
                "panel_id": "hero",
                "role": "primary_anchor",
                "evidence_job": "Show the complete source-matched hero and continuous connector topology.",
                "source_aliases": ["product_front"],
                "invariant_ids": ["inv_identity", "inv_topology"],
                "required_for_acceptance": True,
            },
            {
                "panel_id": "angle_front",
                "role": "multi_angle",
                "evidence_job": "Confirm front proportions and the visible rim junction.",
                "source_aliases": ["product_front"],
                "invariant_ids": ["inv_identity", "inv_structure"],
                "required_for_acceptance": True,
            },
            {
                "panel_id": "angle_three_quarter",
                "role": "multi_angle",
                "evidence_job": "Confirm the continuous connector topology from a complementary angle.",
                "source_aliases": ["product_front"],
                "invariant_ids": ["inv_identity", "inv_topology"],
                "required_for_acceptance": True,
            },
            {
                "panel_id": "angle_side",
                "role": "multi_angle",
                "evidence_job": "Confirm source-matched edge depth and body junction.",
                "source_aliases": ["product_front", "material_macro"],
                "invariant_ids": ["inv_structure", "inv_material"],
                "required_for_acceptance": True,
            },
            {
                "panel_id": "material_edge",
                "role": "material_response",
                "evidence_job": "Show translucent edge depth without inventing internal layers.",
                "source_aliases": ["material_macro"],
                "invariant_ids": ["inv_material"],
                "required_for_acceptance": True,
            },
            {
                "panel_id": "material_highlight",
                "role": "material_response",
                "evidence_job": "Show the source highlight boundary at legible scale.",
                "source_aliases": ["material_macro"],
                "invariant_ids": ["inv_material"],
                "required_for_acceptance": True,
            },
            {
                "panel_id": "structure_join",
                "role": "critical_structure",
                "evidence_job": "Show the visible rim and body join with locating context.",
                "source_aliases": ["product_front"],
                "invariant_ids": ["inv_topology", "inv_structure"],
                "required_for_acceptance": True,
            },
        ],
    }


def build_fixture(
    base: Path,
    *,
    draft_transform: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    run_dir = base / "run"
    original_front = base / "inputs" / "front-reference-wrong.jpg"
    original_macro = base / "inputs" / "macro-reference-wrong.png"
    make_image(
        original_front,
        color=(210, 20, 30, 255),
        size=(160, 120),
        image_format="PNG",
    )
    make_image(
        original_macro,
        color=(20, 210, 30, 255),
        size=(96, 128),
        image_format="JPEG",
    )
    manifest = run_dir / "sources" / "reference-manifest.json"
    freeze_command = [
        sys.executable,
        "-X",
        "utf8",
        str(FREEZER),
        "--run-dir",
        str(run_dir),
        "--manifest",
        str(manifest),
        "--reference",
        f"product_front={original_front}",
        "--reference",
        f"material_macro={original_macro}",
    ]
    frozen = run(freeze_command)
    if frozen.returncode != 0:
        raise AssertionError(frozen.stderr)
    freeze_payload = json.loads(frozen.stdout)
    frozen_paths = [Path(item) for item in freeze_payload["frozen_paths"]]

    draft = source_contract_draft()
    if draft_transform is not None:
        draft_transform(draft)
    ledger = base / "source-ledger-draft.json"
    write_json(ledger, draft)
    contract = run_dir / "sources" / "material-source-contract.json"
    prompt_block = run_dir / "sources" / "material-prompt-block.md"
    contract_command = [
        sys.executable,
        "-X",
        "utf8",
        str(CONTRACT_FREEZER),
        "--run-dir",
        str(run_dir),
        "--reference-manifest",
        str(manifest),
        "--source-ledger",
        str(ledger),
        "--contract",
        str(contract),
        "--prompt-block",
        str(prompt_block),
    ]
    frozen_contract = run(contract_command)
    if frozen_contract.returncode != 0:
        raise AssertionError(frozen_contract.stderr)

    attempt = run_dir / "attempts" / "01"
    attempt.mkdir(parents=True)
    prompt = attempt / "material-test-asset_01_generation_prompt.md"
    prompt.write_bytes(
        b"Create one horizontal material master board.\n\n"
        + prompt_block.read_bytes()
        + b"Preserve every verified invariant and omit unsupported states."
    )
    exec_source = attempt / "worker_exec.js"
    exec_receipt = attempt / "worker_exec.json"
    render_command = [
        sys.executable,
        "-X",
        "utf8",
        str(EXEC_RENDERER),
        "--run-dir",
        str(run_dir),
        "--attempt-dir",
        str(attempt),
        "--worker-run-nonce",
        NONCE,
        "--expected-prompt",
        str(prompt),
        "--reference-manifest",
        str(manifest),
        "--source-contract",
        str(contract),
        "--exec-source",
        str(exec_source),
        "--exec-receipt",
        str(exec_receipt),
    ]
    rendered = run(render_command)
    if rendered.returncode != 0:
        raise AssertionError(rendered.stderr)

    spawn = attempt / "worker_spawn.json"
    spawn_command = [
        sys.executable,
        "-X",
        "utf8",
        str(SPAWN_FREEZER),
        "--run-dir",
        str(run_dir),
        "--attempt-dir",
        str(attempt),
        "--worker-spawn",
        str(spawn),
        "--agent-path",
        AGENT_PATH,
        "--parent-thread-id",
        PARENT_ID,
        "--not-before-ms",
        str(CHECKPOINT),
        "--worker-run-nonce",
        NONCE,
        "--expected-prompt",
        str(prompt),
        "--reference-manifest",
        str(manifest),
        "--source-contract",
        str(contract),
        "--exec-source",
        str(exec_source),
        "--exec-receipt",
        str(exec_receipt),
    ]
    frozen_spawn = run(spawn_command)
    if frozen_spawn.returncode != 0:
        raise AssertionError(frozen_spawn.stderr)

    codex_home = base / "codex-home"
    source_image = codex_home / "generated_images" / THREAD_ID / f"{IMAGE_CALL_ID}.png"
    make_image(
        source_image,
        color=(30, 40, 220, 255),
        size=(1672, 941),
        image_format="PNG",
    )
    rollout = base / "worker-rollout.jsonl"
    events: list[dict[str, Any]] = [
        {
            "type": "session_meta",
            "payload": {
                "id": THREAD_ID,
                "agent_path": AGENT_PATH,
                "parent_thread_id": PARENT_ID,
            },
        },
        {"type": "event_msg", "payload": {"type": "task_started", "turn_id": TURN_ID}},
        {"type": "turn_context", "payload": {"turn_id": TURN_ID}},
        {
            "type": "event_msg",
            "payload": {"type": "user_message", "message": "Execute the frozen source exactly once."},
        },
        {
            "type": "response_item",
            "payload": {
                "type": "custom_tool_call",
                "name": "exec",
                "call_id": "call_image_exec",
                "input": exec_source.read_text(encoding="utf-8"),
            },
        },
        {
            "type": "response_item",
            "payload": {
                "type": "custom_tool_call_output",
                "call_id": "call_image_exec",
                "output": "Script completed\nOutput:\n",
            },
        },
        {
            "type": "event_msg",
            "payload": {
                "type": "image_generation_end",
                "status": "completed",
                "call_id": IMAGE_CALL_ID,
                "saved_path": str(source_image),
            },
        },
        {
            "type": "event_msg",
            "payload": {"type": "agent_message", "phase": "final_answer", "message": ""},
        },
        {
            "type": "response_item",
            "payload": {
                "type": "message",
                "role": "assistant",
                "phase": "final_answer",
                "content": [{"type": "output_text", "text": ""}],
            },
        },
        {
            "type": "event_msg",
            "payload": {"type": "task_complete", "turn_id": TURN_ID, "last_agent_message": None},
        },
    ]
    write_events(rollout, events)
    state_db = base / "state.sqlite"
    connection = sqlite3.connect(state_db)
    connection.execute(
        "CREATE TABLE threads (id TEXT, rollout_path TEXT, created_at INTEGER, created_at_ms INTEGER, source TEXT)"
    )
    source = json.dumps(
        {
            "subagent": {
                "thread_spawn": {"parent_thread_id": PARENT_ID, "agent_path": AGENT_PATH}
            }
        }
    )
    connection.execute(
        "INSERT INTO threads VALUES (?, ?, ?, ?, ?)",
        (THREAD_ID, str(rollout), CHECKPOINT // 1000 + 1, CHECKPOINT + 1, source),
    )
    connection.commit()
    connection.close()
    board = attempt / "board.png"
    result_json = attempt / "worker_result.json"
    resolve_command = [
        sys.executable,
        "-X",
        "utf8",
        str(RESOLVER),
        "--worker-spawn",
        str(spawn),
        "--copy-to",
        str(board),
        "--result-json",
        str(result_json),
        "--state-db",
        str(state_db),
        "--codex-home",
        str(codex_home),
    ]
    return {
        "base": base,
        "run": run_dir,
        "attempt": attempt,
        "manifest": manifest,
        "contract": contract,
        "prompt_block": prompt_block,
        "ledger": ledger,
        "prompt": prompt,
        "exec_source": exec_source,
        "exec_receipt": exec_receipt,
        "spawn": spawn,
        "frozen_paths": frozen_paths,
        "source_image": source_image,
        "rollout": rollout,
        "events": events,
        "state_db": state_db,
        "codex_home": codex_home,
        "board": board,
        "result_json": result_json,
        "resolve_command": resolve_command,
        "freeze_command": freeze_command,
        "contract_command": contract_command,
        "render_command": render_command,
        "spawn_command": spawn_command,
    }


def image_exec_event(fixture: dict[str, Any]) -> dict[str, Any]:
    return next(
        event
        for event in fixture["events"]
        if event.get("type") == "response_item"
        and event.get("payload", {}).get("type") == "custom_tool_call"
    )


def assert_resolver_red_without_new_outputs(
    case: unittest.TestCase,
    fixture: dict[str, Any],
    expected_code: str,
) -> subprocess.CompletedProcess[str]:
    result = run(fixture["resolve_command"])
    case.assertNotEqual(result.returncode, 0, result.stdout)
    case.assertEqual(error_code(result), expected_code, result.stderr)
    case.assertFalse(fixture["board"].exists())
    case.assertFalse(fixture["result_json"].exists())
    return result


def build_publication_fixture(base: Path, external_status: str = "not_ready") -> dict[str, Any]:
    fixture = build_fixture(base)
    resolved = run(fixture["resolve_command"])
    if resolved.returncode != 0:
        raise AssertionError(resolved.stderr)
    worker = json.loads(fixture["result_json"].read_text(encoding="utf-8"))
    manifest = json.loads(fixture["manifest"].read_text(encoding="utf-8"))
    contract = json.loads(fixture["contract"].read_text(encoding="utf-8"))
    attempt = fixture["attempt"]
    enhancement = attempt / "material-test-asset_01_4k_enhancement_prompt.md"
    board_gates = {
        "primary_anchor_clear": "pass",
        "multi_angle_complementary": "pass",
        "material_evidence_present": "pass",
        "material_source_consistent": "pass",
        "material_fidelity": "pass",
        "critical_structure_fidelity": "pass",
        "low_redundancy": "pass",
        "panel_legibility": "pass",
        "single_board_contract": "pass",
        "no_poster_pollution": "pass",
        "video_reference_ready": "pass",
        "prompt_bound": "pass",
        "identity_fidelity": "pass",
        "topology_fidelity": "pass",
        "structure_fidelity": "pass",
        "state_window_source_supported": "not_used",
    }
    defects = [
        {
            "defect_id": "minor_edge_aliasing",
            "category": "artifact",
            "severity": "low",
            "description": "Minor raster aliasing is visible on one neutral-background edge.",
            "panel_ids": ["hero"],
            "invariant_ids": [],
            "source_aliases": ["product_front"],
            "cleanup_eligible": True,
            "cleanup_operation": "reduce_raster_aliasing",
        }
    ]
    source_refs = [
        {"alias": item["alias"], "path": item["frozen_path"], "sha256": item["sha256"]}
        for item in manifest["ordered_references"]
    ]
    enhancement.write_bytes(
        render_4k_enhancement_prompt_bytes(
            board_path=fixture["board"].resolve(strict=False),
            board_sha256=sha256_file(fixture["board"]),
            source_references=source_refs,
            source_contract_path=fixture["contract"].resolve(strict=False),
            source_contract_sha256=sha256_file(fixture["contract"]),
            cleanup_defects=defects,
        )
    )
    qa_decision = attempt / "qa_decision.json"
    sources_by_fact = fact_sources(contract)
    decision_value = {
        "schema_version": "material_board_qa_decision.v1",
        "attempt_id": "01",
        "comparison_mode": "source_to_board_visual_comparison",
        "assistant_qa_status": "passed",
        "production_approval_status": "not_granted",
        "board_gates": board_gates,
        "panel_results": [
            {
                "panel_id": panel["panel_id"],
                "source_aliases": panel["source_aliases"],
                "invariant_ids": panel["invariant_ids"],
                "status": "pass",
                "source_fidelity": "pass",
                "source_observation": f"Sources define the evidence job for {panel['panel_id']}.",
                "board_observation": f"Board visibly preserves the source-bound evidence for {panel['panel_id']}.",
            }
            for panel in contract["panel_plan"]
        ],
        "invariant_results": [
            {
                "invariant_id": invariant["invariant_id"],
                "category": invariant["category"],
                "source_aliases": sources_by_fact[invariant["fact_id"]],
                "status": "pass",
                "source_fidelity": "pass",
                "source_observation": f"Sources establish invariant {invariant['invariant_id']}.",
                "board_observation": f"Board preserves invariant {invariant['invariant_id']} without drift.",
            }
            for invariant in contract["critical_invariants"]
        ],
        "observed_defects": defects,
        "repair_required": False,
        "repair_reasons": [],
    }
    write_json(qa_decision, decision_value)
    manifest_record = {
        "entries": manifest["ordered_references"],
        "aliases": [item["alias"] for item in manifest["ordered_references"]],
    }
    qa = attempt / "qa.json"
    qa_value = build_qa_record(
        decision=decision_value,
        decision_path=qa_decision.resolve(strict=False),
        decision_sha256=sha256_file(qa_decision),
        board_path=fixture["board"].resolve(strict=False),
        board_sha256=sha256_file(fixture["board"]),
        width_px=1672,
        height_px=941,
        worker_thread_id=worker["worker_thread_id"],
        image_generation_call_id=worker["image_generation_call_id"],
        contract=contract,
        manifest=manifest_record,
    )
    write_json(qa, qa_value)
    handoff = attempt / "material-test-asset_01_4k_handoff.json"
    external_states = {
        "not_ready": ("not_started", "not_requested"),
        "handoff_ready": ("not_started", "not_requested"),
        "blocked_runtime_controls": ("not_started", "not_requested"),
        "pending_external_generation": ("pending", "not_requested"),
        "returned_unverified": ("pending", "not_requested"),
        "verified": ("passed", "pending"),
        "rejected": ("failed", "rejected"),
    }
    external_qa_status, external_production_status = external_states[external_status]
    handoff_value = build_handoff_record(
        attempt_id="01",
        generation_prompt_path=fixture["prompt"].resolve(strict=False),
        generation_prompt_sha256=sha256_file(fixture["prompt"]),
        enhancement_prompt_path=enhancement.resolve(strict=False),
        enhancement_prompt_sha256=sha256_file(enhancement),
        inspection_path=qa.resolve(strict=False),
        inspection_sha256=sha256_file(qa),
        board_path=fixture["board"].resolve(strict=False),
        board_sha256=sha256_file(fixture["board"]),
        source_references=source_refs,
        source_contract_path=fixture["contract"].resolve(strict=False),
        source_contract_sha256=sha256_file(fixture["contract"]),
        observed_defects=defects,
        external_status=external_status,
        external_qa_status=external_qa_status,
        external_production_status=external_production_status,
    )
    write_json(handoff, handoff_value)
    accepted_path = fixture["run"] / "accepted_attempt.json"
    accepted = build_accepted_record(attempt_id="01", paths_and_hashes={
        "reference_manifest_path": str(fixture["manifest"].resolve(strict=False)),
        "reference_manifest_sha256": sha256_file(fixture["manifest"]),
        "source_contract_path": str(fixture["contract"].resolve(strict=False)),
        "source_contract_sha256": sha256_file(fixture["contract"]),
        "prompt_block_path": str(fixture["prompt_block"].resolve(strict=False)),
        "prompt_block_sha256": sha256_file(fixture["prompt_block"]),
        "generation_prompt_path": str(fixture["prompt"].resolve(strict=False)),
        "generation_prompt_sha256": sha256_file(fixture["prompt"]),
        "enhancement_prompt_path": str(enhancement.resolve(strict=False)),
        "4k_enhancement_prompt_sha256": sha256_file(enhancement),
        "worker_spawn_path": str(fixture["spawn"].resolve(strict=False)),
        "worker_spawn_sha256": sha256_file(fixture["spawn"]),
        "worker_exec_source_path": str(fixture["exec_source"].resolve(strict=False)),
        "worker_exec_source_sha256": sha256_file(fixture["exec_source"]),
        "worker_exec_receipt_path": str(fixture["exec_receipt"].resolve(strict=False)),
        "worker_exec_receipt_sha256": sha256_file(fixture["exec_receipt"]),
        "worker_result_path": str(fixture["result_json"].resolve(strict=False)),
        "worker_result_sha256": sha256_file(fixture["result_json"]),
        "board_path": str(fixture["board"].resolve(strict=False)),
        "image_sha256": sha256_file(fixture["board"]),
        "inspection_decision_path": str(qa_decision.resolve(strict=False)),
        "inspection_decision_sha256": sha256_file(qa_decision),
        "inspection_path": str(qa.resolve(strict=False)),
        "inspection_sha256": sha256_file(qa),
        "handoff_path": str(handoff.resolve(strict=False)),
        "handoff_sha256": sha256_file(handoff),
    })
    write_json(accepted_path, accepted)
    output = fixture["run"] / "material-test-asset_final_main_result.md"
    builder_command = [
        sys.executable,
        "-X",
        "utf8",
        str(FINAL_BUILDER),
        "--run-dir",
        str(fixture["run"]),
        "--accepted-attempt",
        str(accepted_path),
        "--board",
        str(fixture["board"]),
        "--generation-prompt",
        str(fixture["prompt"]),
        "--enhancement-prompt",
        str(enhancement),
        "--worker-spawn",
        str(fixture["spawn"]),
        "--worker-result",
        str(fixture["result_json"]),
        "--inspection-decision",
        str(qa_decision),
        "--inspection",
        str(qa),
        "--reference-manifest",
        str(fixture["manifest"]),
        "--source-contract",
        str(fixture["contract"]),
        "--handoff",
        str(handoff),
        "--output",
        str(output),
    ]
    inspection_freeze_command = [
        sys.executable,
        "-X",
        "utf8",
        str(INSPECTION_FREEZER),
        "--run-dir",
        str(fixture["run"]),
        "--attempt-dir",
        str(fixture["attempt"]),
        "--board",
        str(fixture["board"]),
        "--worker-result",
        str(fixture["result_json"]),
        "--reference-manifest",
        str(fixture["manifest"]),
        "--source-contract",
        str(fixture["contract"]),
        "--decision-draft",
        str(qa_decision),
        "--inspection",
        str(qa),
    ]
    post_generation_command = [
        sys.executable,
        "-X",
        "utf8",
        str(POST_GENERATION_FREEZER),
        "--run-dir",
        str(fixture["run"]),
        "--attempt-dir",
        str(fixture["attempt"]),
        "--board",
        str(fixture["board"]),
        "--generation-prompt",
        str(fixture["prompt"]),
        "--worker-spawn",
        str(fixture["spawn"]),
        "--worker-result",
        str(fixture["result_json"]),
        "--inspection-decision",
        str(qa_decision),
        "--inspection",
        str(qa),
        "--reference-manifest",
        str(fixture["manifest"]),
        "--source-contract",
        str(fixture["contract"]),
        "--enhancement-prompt",
        str(enhancement),
        "--handoff",
        str(handoff),
        "--accepted-attempt",
        str(accepted_path),
        "--external-4k-status",
        external_status,
        "--external-4k-qa-status",
        external_qa_status,
        "--external-4k-production-approval-status",
        external_production_status,
    ]
    fixture.update(
        {
            "enhancement": enhancement,
            "qa_decision": qa_decision,
            "decision_value": decision_value,
            "qa": qa,
            "qa_value": qa_value,
            "handoff": handoff,
            "handoff_value": handoff_value,
            "accepted_path": accepted_path,
            "accepted": accepted,
            "output": output,
            "builder_command": builder_command,
            "inspection_freeze_command": inspection_freeze_command,
            "post_generation_command": post_generation_command,
        }
    )
    return fixture


def update_accepted_hash(fixture: dict[str, Any], field: str, path: Path) -> None:
    accepted = json.loads(fixture["accepted_path"].read_text(encoding="utf-8"))
    accepted[field] = sha256_file(path)
    write_json(fixture["accepted_path"], accepted)


class ReferenceAndSourceContractTests(unittest.TestCase):
    def test_reference_v2_uses_real_format_metadata_and_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory(prefix="material-v4-freeze-") as temp:
            fixture = build_fixture(Path(temp))
            manifest = json.loads(fixture["manifest"].read_text(encoding="utf-8"))
            entries = manifest["ordered_references"]
            self.assertEqual(manifest["schema_version"], "material_reference_bundle.v2")
            self.assertEqual(entries[0]["detected_format"], "PNG")
            self.assertEqual(entries[0]["mime_type"], "image/png")
            self.assertTrue(entries[0]["frozen_path"].endswith(".png"))
            self.assertEqual(entries[1]["detected_format"], "JPEG")
            self.assertEqual(entries[1]["mime_type"], "image/jpeg")
            self.assertTrue(entries[1]["frozen_path"].endswith(".jpg"))
            before = fixture["manifest"].read_bytes()
            rerun = run(fixture["freeze_command"])
            self.assertEqual(rerun.returncode, 0, rerun.stderr)
            self.assertTrue(json.loads(rerun.stdout)["idempotent"])
            self.assertEqual(fixture["manifest"].read_bytes(), before)

    def test_reference_freezer_conflict_is_red_and_preserves_existing_bytes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="material-v4-freeze-conflict-") as temp:
            fixture = build_fixture(Path(temp))
            manifest_before = fixture["manifest"].read_bytes()
            destination = fixture["frozen_paths"][0]
            destination.write_bytes(b"sentinel-frozen-reference")
            result = run(fixture["freeze_command"])
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(error_code(result), "blocked_reference_bundle_destination_conflict")
            self.assertEqual(destination.read_bytes(), b"sentinel-frozen-reference")
            self.assertEqual(fixture["manifest"].read_bytes(), manifest_before)

    def test_corrupt_reference_is_red_without_run_side_effect(self) -> None:
        with tempfile.TemporaryDirectory(prefix="material-v4-corrupt-ref-") as temp:
            base = Path(temp)
            corrupt = base / "corrupt.png"
            corrupt.write_bytes(b"\x89PNG\r\n\x1a\nnot-a-real-image")
            run_dir = base / "run"
            manifest = run_dir / "sources" / "reference-manifest.json"
            result = run(
                [
                    sys.executable,
                    str(FREEZER),
                    "--run-dir",
                    str(run_dir),
                    "--manifest",
                    str(manifest),
                    "--reference",
                    f"bad_source={corrupt}",
                ]
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(error_code(result), "blocked_reference_image_invalid")
            self.assertFalse(run_dir.exists())

    def test_empty_source_ledger_is_red_without_contract_outputs(self) -> None:
        with tempfile.TemporaryDirectory(prefix="material-v4-empty-ledger-") as temp:
            fixture = build_fixture(Path(temp))
            fixture["contract"].unlink()
            fixture["prompt_block"].unlink()
            fixture["ledger"].write_text("{}\n", encoding="utf-8", newline="\n")
            result = run(fixture["contract_command"])
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(error_code(result), "blocked_material_source_contract_invalid")
            self.assertFalse(fixture["contract"].exists())
            self.assertFalse(fixture["prompt_block"].exists())

    def test_primary_anchor_cannot_use_material_only_source(self) -> None:
        with tempfile.TemporaryDirectory(prefix="material-v4-panel-authority-") as temp:
            fixture = build_fixture(Path(temp))
            fixture["contract"].unlink()
            fixture["prompt_block"].unlink()
            draft = source_contract_draft()
            draft["panel_plan"][0]["source_aliases"] = ["material_macro"]
            write_json(fixture["ledger"], draft)
            result = run(fixture["contract_command"])
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(error_code(result), "blocked_material_source_contract_invalid")
            self.assertFalse(fixture["contract"].exists())
            self.assertFalse(fixture["prompt_block"].exists())

    def test_needs_source_fact_cannot_become_critical_invariant(self) -> None:
        with tempfile.TemporaryDirectory(prefix="material-v4-needs-source-") as temp:
            fixture = build_fixture(Path(temp))
            fixture["contract"].unlink()
            fixture["prompt_block"].unlink()
            draft = source_contract_draft()
            draft["critical_invariants"][0]["category"] = "state"
            draft["critical_invariants"][0]["fact_id"] = "open_state_missing"
            write_json(fixture["ledger"], draft)
            result = run(fixture["contract_command"])
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(error_code(result), "blocked_material_source_contract_invalid")
            self.assertFalse(fixture["contract"].exists())
            self.assertFalse(fixture["prompt_block"].exists())

    def test_preexisting_frozen_symlink_escape_is_red_without_manifest(self) -> None:
        with tempfile.TemporaryDirectory(prefix="material-v4-frozen-link-") as temp:
            base = Path(temp)
            source = base / "outside.png"
            make_image(source, color=(12, 34, 56, 255), size=(64, 48), image_format="PNG")
            run_dir = base / "run"
            references = run_dir / "sources" / "references"
            references.mkdir(parents=True)
            escaped = references / "01_product_front.png"
            escaped.symlink_to(source)
            manifest = run_dir / "sources" / "reference-manifest.json"
            result = run(
                [
                    sys.executable,
                    "-X",
                    "utf8",
                    str(FREEZER),
                    "--run-dir",
                    str(run_dir),
                    "--manifest",
                    str(manifest),
                    "--reference",
                    f"product_front={source}",
                ]
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(error_code(result), "blocked_reference_bundle_location")
            self.assertFalse(manifest.exists())
            self.assertTrue(escaped.is_symlink())


class ResolverV4Tests(unittest.TestCase):
    def test_green_resolver_binds_real_non_exact_16_9_png(self) -> None:
        with tempfile.TemporaryDirectory(prefix="material-v4-resolve-green-") as temp:
            fixture = build_fixture(Path(temp))
            result = run(fixture["resolve_command"])
            self.assertEqual(result.returncode, 0, result.stderr)
            record = json.loads(fixture["result_json"].read_text(encoding="utf-8"))
            self.assertEqual(record["schema_version"], "delegated_product_image_worker_result.v2")
            self.assertEqual(record["png_validation"], "pillow_verify_and_full_load")
            self.assertEqual((record["width_px"], record["height_px"]), (1672, 941))
            self.assertFalse(record["exact_16_9"])
            self.assertTrue(record["output_distinct_from_all_sources"])

    def test_comment_and_bracket_exec_bypasses_are_red_without_outputs(self) -> None:
        for suffix in ("\n// decoy comment", "\n[]"):
            with self.subTest(suffix=suffix), tempfile.TemporaryDirectory(
                prefix="material-v4-exec-bypass-"
            ) as temp:
                fixture = build_fixture(Path(temp))
                image_exec_event(fixture)["payload"]["input"] += suffix
                write_events(fixture["rollout"], fixture["events"])
                assert_resolver_red_without_new_outputs(
                    self, fixture, "blocked_worker_exec_source_mismatch"
                )

    def test_earlier_turn_is_red_without_outputs(self) -> None:
        with tempfile.TemporaryDirectory(prefix="material-v4-earlier-turn-") as temp:
            fixture = build_fixture(Path(temp))
            previous_turn = "019f0000-0000-7000-8000-000000000099"
            fixture["events"][1:1] = [
                {"type": "event_msg", "payload": {"type": "task_started", "turn_id": previous_turn}},
                {"type": "turn_context", "payload": {"turn_id": previous_turn}},
                {
                    "type": "event_msg",
                    "payload": {"type": "task_complete", "turn_id": previous_turn, "last_agent_message": None},
                },
            ]
            write_events(fixture["rollout"], fixture["events"])
            assert_resolver_red_without_new_outputs(self, fixture, "blocked_worker_task_count")

    def test_unknown_call_is_fail_closed_without_outputs(self) -> None:
        with tempfile.TemporaryDirectory(prefix="material-v4-unknown-call-") as temp:
            fixture = build_fixture(Path(temp))
            fixture["events"].insert(
                4,
                {
                    "type": "response_item",
                    "payload": {
                        "type": "mcp_tool_call",
                        "name": "unknown",
                        "call_id": "unknown_call",
                    },
                },
            )
            write_events(fixture["rollout"], fixture["events"])
            assert_resolver_red_without_new_outputs(
                self, fixture, "blocked_worker_unexpected_tool_call"
            )

    def test_event_message_call_shape_is_fail_closed_without_outputs(self) -> None:
        with tempfile.TemporaryDirectory(prefix="material-v4-event-call-") as temp:
            fixture = build_fixture(Path(temp))
            fixture["events"].insert(
                4,
                {
                    "type": "event_msg",
                    "payload": {
                        "type": "mcp_tool_call",
                        "name": "unknown",
                        "call_id": "event_call",
                    },
                },
            )
            write_events(fixture["rollout"], fixture["events"])
            assert_resolver_red_without_new_outputs(
                self, fixture, "blocked_worker_unexpected_tool_call"
            )

    def test_unknown_call_output_shape_is_fail_closed_without_outputs(self) -> None:
        with tempfile.TemporaryDirectory(prefix="material-v4-output-shape-") as temp:
            fixture = build_fixture(Path(temp))
            fixture["events"][5]["payload"]["type"] = "attacker_defined_call_output"
            write_events(fixture["rollout"], fixture["events"])
            assert_resolver_red_without_new_outputs(
                self, fixture, "blocked_worker_unexpected_tool_call"
            )

    def test_corrupt_generated_png_is_red_without_outputs(self) -> None:
        with tempfile.TemporaryDirectory(prefix="material-v4-corrupt-png-") as temp:
            fixture = build_fixture(Path(temp))
            fixture["source_image"].write_bytes(b"\x89PNG\r\n\x1a\ntruncated")
            assert_resolver_red_without_new_outputs(self, fixture, "blocked_worker_image_invalid")

    def test_historical_44_character_shell_wrapper_is_red_without_outputs(self) -> None:
        with tempfile.TemporaryDirectory(prefix="material-v4-wrapper-") as temp:
            fixture = build_fixture(Path(temp))
            wrapper = "Exit code: 0\nWall time: 0.1 seconds\nOutput:\n"
            self.assertEqual(len(wrapper), 44)
            wrapped_exec = render_worker_exec_bytes(
                NONCE,
                wrapper + fixture["prompt"].read_text(encoding="utf-8"),
                fixture["frozen_paths"],
            ).decode("utf-8")
            image_exec_event(fixture)["payload"]["input"] = wrapped_exec
            write_events(fixture["rollout"], fixture["events"])
            assert_resolver_red_without_new_outputs(
                self, fixture, "blocked_worker_exec_source_mismatch"
            )

    def test_wait_after_completed_image_is_red_without_outputs(self) -> None:
        with tempfile.TemporaryDirectory(prefix="material-v4-late-wait-") as temp:
            fixture = build_fixture(Path(temp))
            fixture["events"][5]["payload"]["output"] = "Script running with cell ID image_cell_1"
            fixture["events"][7:7] = [
                {
                    "type": "response_item",
                    "payload": {
                        "type": "function_call",
                        "name": "wait",
                        "call_id": "call_wait_late",
                        "arguments": json.dumps({"cell_id": "image_cell_1"}),
                    },
                },
                {
                    "type": "response_item",
                    "payload": {
                        "type": "function_call_output",
                        "call_id": "call_wait_late",
                        "output": "Script completed\nOutput:\n",
                    },
                },
            ]
            write_events(fixture["rollout"], fixture["events"])
            assert_resolver_red_without_new_outputs(self, fixture, "blocked_worker_event_order")

    def test_mutated_source_contract_is_red_without_outputs(self) -> None:
        with tempfile.TemporaryDirectory(prefix="material-v4-mutated-contract-") as temp:
            fixture = build_fixture(Path(temp))
            contract = json.loads(fixture["contract"].read_text(encoding="utf-8"))
            contract["source_authority"][0]["exclusions"].append("post-freeze mutation")
            write_json(fixture["contract"], contract)
            result = run(fixture["resolve_command"])
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(fixture["board"].exists())
            self.assertFalse(fixture["result_json"].exists())

    def test_explicit_paths_v1_production_bypass_is_stably_blocked(self) -> None:
        with tempfile.TemporaryDirectory(prefix="material-v4-explicit-bypass-") as temp:
            base = Path(temp)
            prompt = base / "prompt.md"
            reference = base / "reference.png"
            prompt.write_text("legacy prompt", encoding="utf-8")
            make_image(reference, color=(1, 2, 3, 255), size=(64, 64), image_format="PNG")
            board = base / "board.png"
            result_json = base / "result.json"
            result = run(
                [
                    sys.executable,
                    str(RESOLVER),
                    "--agent-path",
                    AGENT_PATH,
                    "--not-before-ms",
                    "0",
                    "--parent-thread-id",
                    PARENT_ID,
                    "--worker-run-nonce",
                    NONCE,
                    "--expected-prompt",
                    str(prompt),
                    "--expected-reference",
                    str(reference),
                    "--copy-to",
                    str(board),
                    "--result-json",
                    str(result_json),
                ]
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(error_code(result), "blocked_legacy_material_run_v1")
            self.assertFalse(board.exists())
            self.assertFalse(result_json.exists())

    def test_mixed_v1_and_v4_resolver_arguments_are_stably_blocked(self) -> None:
        with tempfile.TemporaryDirectory(prefix="material-v4-mixed-legacy-") as temp:
            fixture = build_fixture(Path(temp))
            result = run(fixture["resolve_command"] + ["--agent-path", AGENT_PATH])
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(error_code(result), "blocked_legacy_material_run_v1")
            self.assertFalse(fixture["board"].exists())
            self.assertFalse(fixture["result_json"].exists())

    def test_reference_manifest_v1_is_stably_blocked_without_outputs(self) -> None:
        with tempfile.TemporaryDirectory(prefix="material-v4-legacy-manifest-") as temp:
            fixture = build_fixture(Path(temp))
            manifest = json.loads(fixture["manifest"].read_text(encoding="utf-8"))
            manifest["schema_version"] = "material_reference_bundle.v1"
            write_json(fixture["manifest"], manifest)
            assert_resolver_red_without_new_outputs(
                self, fixture, "blocked_legacy_material_run_v1"
            )

    def test_reference_manifest_symlink_escape_is_red_without_outputs(self) -> None:
        with tempfile.TemporaryDirectory(prefix="material-v4-manifest-link-") as temp:
            fixture = build_fixture(Path(temp))
            outside = Path(temp) / "outside-reference-manifest.json"
            fixture["manifest"].replace(outside)
            fixture["manifest"].symlink_to(outside)
            result = run(fixture["resolve_command"])
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(error_code(result), "blocked_reference_manifest_invalid")
            self.assertFalse(fixture["board"].exists())
            self.assertFalse(fixture["result_json"].exists())

    def test_output_overwrite_is_red_and_preserves_sentinel(self) -> None:
        with tempfile.TemporaryDirectory(prefix="material-v4-overwrite-") as temp:
            fixture = build_fixture(Path(temp))
            fixture["board"].write_bytes(b"sentinel-board")
            result = run(fixture["resolve_command"])
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(error_code(result), "blocked_worker_output_conflict")
            self.assertEqual(fixture["board"].read_bytes(), b"sentinel-board")
            self.assertFalse(fixture["result_json"].exists())

    def test_generated_output_identical_to_source_is_red_without_outputs(self) -> None:
        with tempfile.TemporaryDirectory(prefix="material-v4-output-distinct-") as temp:
            fixture = build_fixture(Path(temp))
            fixture["source_image"].write_bytes(fixture["frozen_paths"][0].read_bytes())
            assert_resolver_red_without_new_outputs(
                self, fixture, "blocked_worker_output_matches_source"
            )


class PostGenerationV5Tests(unittest.TestCase):
    def test_scaffold_prefills_source_bindings_and_unfinished_draft_cannot_freeze(self) -> None:
        with tempfile.TemporaryDirectory(prefix="material-v5-qa-scaffold-") as temp:
            fixture = build_fixture(Path(temp))
            resolved = run(fixture["resolve_command"])
            self.assertEqual(resolved.returncode, 0, resolved.stderr)
            decision = fixture["attempt"] / "qa_decision.json"
            qa = fixture["attempt"] / "qa.json"
            scaffold = run(
                [
                    sys.executable,
                    "-X",
                    "utf8",
                    str(INSPECTION_SCAFFOLDER),
                    "--run-dir",
                    str(fixture["run"]),
                    "--attempt-dir",
                    str(fixture["attempt"]),
                    "--reference-manifest",
                    str(fixture["manifest"]),
                    "--source-contract",
                    str(fixture["contract"]),
                    "--decision-draft",
                    str(decision),
                ]
            )
            self.assertEqual(scaffold.returncode, 0, scaffold.stderr)
            value = json.loads(decision.read_text(encoding="utf-8"))
            self.assertEqual(value["comparison_mode"], "source_to_board_visual_comparison")
            self.assertTrue(all(item["source_aliases"] for item in value["panel_results"]))
            self.assertTrue(all(item["source_aliases"] for item in value["invariant_results"]))
            self.assertTrue(all(item["source_observation"] == "" for item in value["panel_results"]))
            self.assertTrue(all(item["source_observation"] == "" for item in value["invariant_results"]))
            self.assertTrue(all(item["board_observation"] == "" for item in value["invariant_results"]))
            frozen = run(
                [
                    sys.executable,
                    "-X",
                    "utf8",
                    str(INSPECTION_FREEZER),
                    "--run-dir",
                    str(fixture["run"]),
                    "--attempt-dir",
                    str(fixture["attempt"]),
                    "--board",
                    str(fixture["board"]),
                    "--worker-result",
                    str(fixture["result_json"]),
                    "--reference-manifest",
                    str(fixture["manifest"]),
                    "--source-contract",
                    str(fixture["contract"]),
                    "--decision-draft",
                    str(decision),
                    "--inspection",
                    str(qa),
                ]
            )
            self.assertNotEqual(frozen.returncode, 0)
            self.assertEqual(error_code(frozen), "blocked_board_inspection_invalid")
            self.assertFalse(qa.exists())

    def test_complete_inspection_and_post_generation_freezers_are_idempotent(self) -> None:
        with tempfile.TemporaryDirectory(prefix="material-v5-freezer-idempotent-") as temp:
            fixture = build_publication_fixture(Path(temp))
            inspection = run(fixture["inspection_freeze_command"])
            self.assertEqual(inspection.returncode, 0, inspection.stderr)
            self.assertFalse(json.loads(inspection.stdout)["created"])
            post = run(fixture["post_generation_command"])
            self.assertEqual(post.returncode, 0, post.stderr)
            self.assertEqual(
                json.loads(post.stdout)["created"],
                {"accepted_attempt": False, "enhancement_prompt": False, "handoff": False},
            )

    def test_source_observation_cannot_be_reused_as_board_observation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="material-v5-observation-copy-") as temp:
            fixture = build_publication_fixture(Path(temp))
            fixture["qa"].unlink()
            decision = json.loads(fixture["qa_decision"].read_text(encoding="utf-8"))
            decision["invariant_results"][0]["board_observation"] = decision[
                "invariant_results"
            ][0]["source_observation"]
            write_json(fixture["qa_decision"], decision)
            frozen = run(fixture["inspection_freeze_command"])
            self.assertNotEqual(frozen.returncode, 0)
            self.assertEqual(error_code(frozen), "blocked_board_inspection_invalid")
            self.assertFalse(fixture["qa"].exists())

    def test_post_generation_freezer_creates_commit_last_and_builder_accepts_it(self) -> None:
        with tempfile.TemporaryDirectory(prefix="material-v5-freezer-green-") as temp:
            fixture = build_publication_fixture(Path(temp))
            for path in (fixture["accepted_path"], fixture["handoff"], fixture["enhancement"]):
                path.unlink()
            result = run(fixture["post_generation_command"])
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                json.loads(result.stdout)["created"],
                {"accepted_attempt": True, "enhancement_prompt": True, "handoff": True},
            )
            self.assertTrue(fixture["accepted_path"].is_file())
            built = run(fixture["builder_command"])
            self.assertEqual(built.returncode, 0, built.stderr)

    def test_post_generation_preflight_conflict_never_writes_accepted_commit(self) -> None:
        with tempfile.TemporaryDirectory(prefix="material-v5-freezer-conflict-") as temp:
            fixture = build_publication_fixture(Path(temp))
            fixture["accepted_path"].unlink()
            fixture["handoff"].write_bytes(b"conflicting-handoff")
            result = run(fixture["post_generation_command"])
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(error_code(result), "blocked_post_generation_output_conflict")
            self.assertEqual(fixture["handoff"].read_bytes(), b"conflicting-handoff")
            self.assertFalse(fixture["accepted_path"].exists())

    def test_post_generation_reaudits_worker_rollout_before_acceptance(self) -> None:
        with tempfile.TemporaryDirectory(prefix="material-v5-freezer-rollout-") as temp:
            fixture = build_publication_fixture(Path(temp))
            for path in (fixture["accepted_path"], fixture["handoff"], fixture["enhancement"]):
                path.unlink()
            earlier_turn = "019f0000-0000-7000-8000-000000000098"
            fixture["events"][1:1] = [
                {"type": "event_msg", "payload": {"type": "task_started", "turn_id": earlier_turn}},
                {"type": "turn_context", "payload": {"turn_id": earlier_turn}},
                {
                    "type": "event_msg",
                    "payload": {
                        "type": "task_complete",
                        "turn_id": earlier_turn,
                        "last_agent_message": None,
                    },
                },
            ]
            write_events(fixture["rollout"], fixture["events"])
            result = run(fixture["post_generation_command"])
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(error_code(result), "blocked_worker_task_count")
            self.assertFalse(fixture["accepted_path"].exists())
            self.assertFalse(fixture["handoff"].exists())
            self.assertFalse(fixture["enhancement"].exists())

    def test_post_generation_rejects_spawn_mutation_before_acceptance(self) -> None:
        with tempfile.TemporaryDirectory(prefix="material-v5-freezer-spawn-") as temp:
            fixture = build_publication_fixture(Path(temp))
            for path in (fixture["accepted_path"], fixture["handoff"], fixture["enhancement"]):
                path.unlink()
            spawn = json.loads(fixture["spawn"].read_text(encoding="utf-8"))
            spawn["pre_spawn_state"] = "mutated_after_resolver"
            write_json(fixture["spawn"], spawn)
            result = run(fixture["post_generation_command"])
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(error_code(result), "blocked_post_generation_records_invalid")
            self.assertFalse(fixture["accepted_path"].exists())
            self.assertFalse(fixture["handoff"].exists())
            self.assertFalse(fixture["enhancement"].exists())


class FinalBuilderV5Tests(unittest.TestCase):
    def test_green_builder_keeps_actual_external_status_and_non_exact_dimensions(self) -> None:
        with tempfile.TemporaryDirectory(prefix="material-v4-builder-green-") as temp:
            fixture = build_publication_fixture(Path(temp), external_status="not_ready")
            result = run(fixture["builder_command"])
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = fixture["output"].read_text(encoding="utf-8")
            self.assertIn("external_4k_status: not_ready", payload)
            self.assertIn("observed_pixel_dimensions: 1672x941", payload)
            self.assertIn("main_result_prompt_pair_status: published", payload)

    def test_enhancement_renderer_is_exact_and_idempotent(self) -> None:
        with tempfile.TemporaryDirectory(prefix="material-v4-4k-render-") as temp:
            fixture = build_publication_fixture(Path(temp))
            before = fixture["enhancement"].read_bytes()
            result = run(
                [
                    sys.executable,
                    "-X",
                    "utf8",
                    str(ENHANCEMENT_RENDERER),
                    "--run-dir",
                    str(fixture["run"]),
                    "--attempt-dir",
                    str(fixture["attempt"]),
                    "--board",
                    str(fixture["board"]),
                    "--inspection",
                    str(fixture["qa"]),
                    "--reference-manifest",
                    str(fixture["manifest"]),
                    "--source-contract",
                    str(fixture["contract"]),
                    "--enhancement-prompt",
                    str(fixture["enhancement"]),
                ]
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(json.loads(result.stdout)["idempotent"])
            self.assertEqual(fixture["enhancement"].read_bytes(), before)

    def test_defect_source_aliases_are_required(self) -> None:
        with tempfile.TemporaryDirectory(prefix="material-v4-defect-sources-") as temp:
            fixture = build_publication_fixture(Path(temp))
            qa = json.loads(fixture["qa"].read_text(encoding="utf-8"))
            del qa["observed_defects"][0]["source_aliases"]
            write_json(fixture["qa"], qa)
            update_accepted_hash(fixture, "inspection_sha256", fixture["qa"])
            result = run(fixture["builder_command"])
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(error_code(result), "blocked_board_inspection_invalid")
            self.assertFalse(fixture["output"].exists())

    def test_material_state_defect_cannot_be_marked_cleanup_eligible(self) -> None:
        with tempfile.TemporaryDirectory(prefix="material-v4-material-cleanup-") as temp:
            fixture = build_publication_fixture(Path(temp))
            qa = json.loads(fixture["qa"].read_text(encoding="utf-8"))
            defect = qa["observed_defects"][0]
            defect.update(
                {
                    "category": "material",
                    "severity": "high",
                    "description": "Source-supported fill boundary and internal material state differ.",
                    "panel_ids": ["material_edge"],
                    "invariant_ids": ["inv_material"],
                    "source_aliases": ["material_macro"],
                    "cleanup_eligible": True,
                    "cleanup_operation": "reduce_raster_aliasing",
                }
            )
            write_json(fixture["qa"], qa)
            update_accepted_hash(fixture, "inspection_sha256", fixture["qa"])
            result = run(fixture["builder_command"])
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(error_code(result), "blocked_board_inspection_invalid")
            self.assertFalse(fixture["output"].exists())

    def test_forbidden_free_prose_4k_prompt_is_red_even_when_hashes_are_updated(self) -> None:
        with tempfile.TemporaryDirectory(prefix="material-v4-4k-prose-") as temp:
            fixture = build_publication_fixture(Path(temp))
            fixture["enhancement"].write_text(
                "Change silhouette, connector topology, fill boundary, label identity, facets, "
                "highlights, material microdetail, and panel order.",
                encoding="utf-8",
                newline="\n",
            )
            handoff = json.loads(fixture["handoff"].read_text(encoding="utf-8"))
            handoff["enhancement_prompt_sha256"] = sha256_file(fixture["enhancement"])
            write_json(fixture["handoff"], handoff)
            update_accepted_hash(
                fixture, "4k_enhancement_prompt_sha256", fixture["enhancement"]
            )
            update_accepted_hash(fixture, "handoff_sha256", fixture["handoff"])
            result = run(fixture["builder_command"])
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(error_code(result), "blocked_4k_prompt_contract_invalid")
            self.assertFalse(fixture["output"].exists())

    def test_external_status_qa_approval_matrix_is_fail_closed(self) -> None:
        contradictory = [
            ("not_ready", "passed", "not_requested"),
            ("handoff_ready", "failed", "not_requested"),
            ("blocked_runtime_controls", "passed", "not_requested"),
        ]
        for external_status, qa_status, production_status in contradictory:
            with self.subTest(status=external_status), tempfile.TemporaryDirectory(
                prefix="material-v4-external-matrix-"
            ) as temp:
                fixture = build_publication_fixture(Path(temp), external_status=external_status)
                handoff = json.loads(fixture["handoff"].read_text(encoding="utf-8"))
                handoff["external_4k_qa_status"] = qa_status
                handoff["external_4k_production_approval_status"] = production_status
                write_json(fixture["handoff"], handoff)
                update_accepted_hash(fixture, "handoff_sha256", fixture["handoff"])
                result = run(fixture["builder_command"])
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(error_code(result), "blocked_4k_handoff_invalid")
                self.assertFalse(fixture["output"].exists())

    def test_accepted_attempt_direct_exec_hash_lock_is_enforced(self) -> None:
        with tempfile.TemporaryDirectory(prefix="material-v4-accepted-exec-") as temp:
            fixture = build_publication_fixture(Path(temp))
            accepted = json.loads(fixture["accepted_path"].read_text(encoding="utf-8"))
            accepted["worker_exec_source_sha256"] = "0" * 64
            write_json(fixture["accepted_path"], accepted)
            result = run(fixture["builder_command"])
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(error_code(result), "blocked_accepted_attempt_mismatch")
            self.assertFalse(fixture["output"].exists())

    def test_handoff_requires_generation_path_and_external_production_state(self) -> None:
        for field in ("generation_prompt_path", "external_4k_production_approval_status"):
            with self.subTest(field=field), tempfile.TemporaryDirectory(
                prefix="material-v4-handoff-field-"
            ) as temp:
                fixture = build_publication_fixture(Path(temp))
                handoff = json.loads(fixture["handoff"].read_text(encoding="utf-8"))
                del handoff[field]
                write_json(fixture["handoff"], handoff)
                update_accepted_hash(fixture, "handoff_sha256", fixture["handoff"])
                result = run(fixture["builder_command"])
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(error_code(result), "blocked_4k_handoff_invalid")
                self.assertFalse(fixture["output"].exists())

    def test_builder_reaudits_mutated_worker_rollout(self) -> None:
        with tempfile.TemporaryDirectory(prefix="material-v4-builder-rollout-") as temp:
            fixture = build_publication_fixture(Path(temp))
            earlier_turn = "019f0000-0000-7000-8000-000000000099"
            fixture["events"][1:1] = [
                {"type": "event_msg", "payload": {"type": "task_started", "turn_id": earlier_turn}},
                {"type": "turn_context", "payload": {"turn_id": earlier_turn}},
                {
                    "type": "event_msg",
                    "payload": {
                        "type": "task_complete",
                        "turn_id": earlier_turn,
                        "last_agent_message": None,
                    },
                },
            ]
            write_events(fixture["rollout"], fixture["events"])
            result = run(fixture["builder_command"])
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(error_code(result), "blocked_worker_task_count")
            self.assertFalse(fixture["output"].exists())

    def test_builder_rejects_falsified_worker_result_runtime_evidence(self) -> None:
        mutations = {
            "missing_rollout": lambda worker, fixture: worker.__setitem__(
                "worker_rollout_path", str(Path(fixture["run"]) / "missing-rollout.jsonl")
            ),
            "missing_saved_image": lambda worker, fixture: worker.__setitem__(
                "worker_saved_path", str(Path(fixture["run"]) / "missing-generated.png")
            ),
            "falsified_aspect": lambda worker, fixture: (
                worker.__setitem__("observed_aspect_ratio", 16 / 9),
                worker.__setitem__("exact_16_9", True),
            ),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory(
                prefix="material-v4-worker-runtime-"
            ) as temp:
                fixture = build_publication_fixture(Path(temp))
                worker = json.loads(fixture["result_json"].read_text(encoding="utf-8"))
                mutate(worker, fixture)
                write_json(fixture["result_json"], worker)
                update_accepted_hash(fixture, "worker_result_sha256", fixture["result_json"])
                result = run(fixture["builder_command"])
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(
                    error_code(result),
                    {"blocked_worker_result_invalid", "blocked_publication_provenance_mismatch"},
                )
                self.assertFalse(fixture["output"].exists())

    def test_topology_invariant_false_pass_requires_repair_without_output(self) -> None:
        with tempfile.TemporaryDirectory(prefix="material-v4-topology-invariant-") as temp:
            fixture = build_publication_fixture(Path(temp))
            qa = json.loads(fixture["qa"].read_text(encoding="utf-8"))
            topology = next(
                item for item in qa["invariant_results"] if item["category"] == "topology"
            )
            topology["status"] = "fail"
            topology["source_fidelity"] = "fail"
            topology["observed_content"] = "Connector count and ordering drift across panels."
            self.assertEqual(qa["assistant_qa_status"], "passed")
            write_json(fixture["qa"], qa)
            update_accepted_hash(fixture, "inspection_sha256", fixture["qa"])
            result = run(fixture["builder_command"])
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(error_code(result), "blocked_board_inspection_invalid")
            self.assertFalse(fixture["output"].exists())

    def test_historical_topology_drift_defect_cannot_hide_behind_all_pass_labels(self) -> None:
        with tempfile.TemporaryDirectory(prefix="material-v4-topology-defect-") as temp:
            fixture = build_publication_fixture(Path(temp))
            qa = json.loads(fixture["qa"].read_text(encoding="utf-8"))
            qa["observed_defects"].append(
                {
                    "defect_id": "cross_panel_link_topology_drift",
                    "category": "topology",
                    "severity": "high",
                    "description": "The connector count and ordering change between hero and angle panels.",
                    "panel_ids": ["hero", "angle_three_quarter"],
                    "invariant_ids": ["inv_topology"],
                    "source_aliases": ["product_front"],
                    "cleanup_eligible": False,
                    "cleanup_operation": "none",
                }
            )
            self.assertTrue(all(value in {"pass", "not_used"} for value in qa["board_gates"].values()))
            self.assertTrue(all(item["status"] == "pass" for item in qa["invariant_results"]))
            write_json(fixture["qa"], qa)
            update_accepted_hash(fixture, "inspection_sha256", fixture["qa"])
            result = run(fixture["builder_command"])
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(error_code(result), "blocked_board_inspection_invalid")
            self.assertFalse(fixture["output"].exists())

    def test_handoff_missing_status_is_red_without_output(self) -> None:
        with tempfile.TemporaryDirectory(prefix="material-v4-handoff-missing-") as temp:
            fixture = build_publication_fixture(Path(temp))
            handoff = json.loads(fixture["handoff"].read_text(encoding="utf-8"))
            del handoff["external_4k_status"]
            write_json(fixture["handoff"], handoff)
            update_accepted_hash(fixture, "handoff_sha256", fixture["handoff"])
            result = run(fixture["builder_command"])
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(error_code(result), "blocked_4k_handoff_invalid")
            self.assertFalse(fixture["output"].exists())

    def test_final_output_overwrite_is_red_and_preserves_sentinel(self) -> None:
        with tempfile.TemporaryDirectory(prefix="material-v4-final-overwrite-") as temp:
            fixture = build_publication_fixture(Path(temp))
            fixture["output"].write_bytes(b"sentinel-final")
            result = run(fixture["builder_command"])
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(error_code(result), "blocked_publication_output_conflict")
            self.assertEqual(fixture["output"].read_bytes(), b"sentinel-final")

    def test_missing_panel_result_is_red_without_output(self) -> None:
        with tempfile.TemporaryDirectory(prefix="material-v4-panel-missing-") as temp:
            fixture = build_publication_fixture(Path(temp))
            qa = json.loads(fixture["qa"].read_text(encoding="utf-8"))
            qa["panel_results"].pop()
            write_json(fixture["qa"], qa)
            update_accepted_hash(fixture, "inspection_sha256", fixture["qa"])
            result = run(fixture["builder_command"])
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(error_code(result), "blocked_board_inspection_invalid")
            self.assertFalse(fixture["output"].exists())

    def test_legacy_accepted_v1_and_v2_are_stably_blocked_without_output(self) -> None:
        for schema in ("material_accepted_attempt.v1", "material_accepted_attempt.v2"):
            with self.subTest(schema=schema), tempfile.TemporaryDirectory(
                prefix="material-v5-legacy-accepted-"
            ) as temp:
                fixture = build_publication_fixture(Path(temp))
                accepted = json.loads(fixture["accepted_path"].read_text(encoding="utf-8"))
                accepted["schema_version"] = schema
                write_json(fixture["accepted_path"], accepted)
                result = run(fixture["builder_command"])
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(error_code(result), "blocked_legacy_material_run_v1")
                self.assertFalse(fixture["output"].exists())

    def test_mutated_source_contract_is_red_without_output(self) -> None:
        with tempfile.TemporaryDirectory(prefix="material-v4-builder-contract-") as temp:
            fixture = build_publication_fixture(Path(temp))
            fixture["contract"].write_text("{}\n", encoding="utf-8", newline="\n")
            result = run(fixture["builder_command"])
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(fixture["output"].exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
