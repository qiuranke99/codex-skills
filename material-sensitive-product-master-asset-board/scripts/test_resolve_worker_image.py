#!/usr/bin/env python3
"""Self-contained contract tests for the material image-worker resolver."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
RESOLVER = SCRIPT_DIR / "resolve_worker_image.py"
FREEZER = SCRIPT_DIR / "freeze_reference_bundle.py"
FINAL_BUILDER = SCRIPT_DIR / "build_final_result.py"


def png_bytes(width: int = 1672, height: int = 941) -> bytes:
    return (
        b"\x89PNG\r\n\x1a\n"
        + struct.pack(">I", 13)
        + b"IHDR"
        + struct.pack(">II", width, height)
        + bytes([8, 6, 0, 0, 0])
        + b"\x00\x00\x00\x00"
    )


def image_call_input(
    prompt: str,
    *,
    references: list[Path] | None = None,
    recent_count: int | None = None,
    nonce: str = "0123456789abcdef0123456789abcdef",
) -> str:
    arguments: dict[str, Any] = {"prompt": prompt}
    if references is not None:
        arguments["referenced_image_paths"] = [str(path) for path in references]
    if recent_count is not None:
        arguments["num_last_images_to_include"] = recent_count
    return (
        f'const worker_run_nonce = "{nonce}";\n'
        "const result = await tools.image_gen__imagegen("
        + json.dumps(arguments, ensure_ascii=False)
        + "); generatedImage(result);"
    )


def write_events(path: Path, events: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(event, ensure_ascii=False) + "\n" for event in events),
        encoding="utf-8",
        newline="\n",
    )


def freeze_manifest(base: Path, original_references: list[Path]) -> tuple[Path, list[Path]]:
    run_dir = base / "run"
    manifest = run_dir / "sources" / "reference-manifest.json"
    command = [
        sys.executable,
        "-X",
        "utf8",
        str(FREEZER),
        "--run-dir",
        str(run_dir),
        "--manifest",
        str(manifest),
    ]
    for index, reference in enumerate(original_references, 1):
        command.extend(["--reference", f"source_{index}={reference}"])
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
    if result.returncode != 0:
        raise AssertionError(result.stderr)
    payload = json.loads(result.stdout)
    return manifest, [Path(path) for path in payload["frozen_paths"]]


def build_fixture(base: Path, mode: str = "explicit") -> dict[str, Any]:
    codex_home = base / "codex_home"
    codex_home.mkdir(parents=True)
    agent_path = "/root/material-image-worker-0123456789abcdef0123456789abcdef"
    parent_id = "019f0000-0000-7000-8000-000000000001"
    thread_id = "019f0000-0000-7000-8000-000000000002"
    turn_id = "019f0000-0000-7000-8000-000000000003"
    call_id = "exec-11111111-2222-4333-8444-555555555555"
    nonce = "0123456789abcdef0123456789abcdef"
    checkpoint = 1_750_000_000_000
    prompt = "Create one material-sensitive product board.\nPreserve exact material evidence."
    prompt_path = base / "attempts" / "01" / "asset_01_generation_prompt.md"
    prompt_path.parent.mkdir(parents=True)
    prompt_path.write_bytes(prompt.encode("utf-8"))

    originals = [base / "inputs" / "front.png", base / "inputs" / "material_macro.png"]
    originals[0].parent.mkdir(parents=True)
    originals[0].write_bytes(b"front-reference")
    originals[1].write_bytes(b"material-reference")
    manifest: Path | None = None
    if mode == "manifest":
        manifest, references = freeze_manifest(base, originals)
        call_input = image_call_input(prompt, references=references)
    elif mode == "explicit":
        references = originals
        call_input = image_call_input(prompt, references=references)
    elif mode == "recent":
        references = []
        call_input = image_call_input(prompt, recent_count=2)
    else:
        raise ValueError(mode)

    source_image = codex_home / "generated_images" / thread_id / f"{call_id}.png"
    source_image.parent.mkdir(parents=True)
    source_image.write_bytes(png_bytes())
    rollout = base / "worker-rollout.jsonl"
    events: list[dict[str, Any]] = [
        {
            "type": "session_meta",
            "payload": {
                "id": thread_id,
                "agent_path": agent_path,
                "parent_thread_id": parent_id,
            },
        },
        {"type": "event_msg", "payload": {"type": "task_started", "turn_id": turn_id}},
        {"type": "turn_context", "payload": {"turn_id": turn_id}},
        {
            "type": "event_msg",
            "payload": {
                "type": "user_message",
                "message": f"worker_run_nonce: {nonce}\nSubmit the frozen prompt once and stop.",
            },
        },
        {
            "type": "response_item",
            "payload": {
                "type": "custom_tool_call",
                "name": "exec",
                "call_id": "call_image_exec",
                "input": call_input,
            },
        },
        {
            "type": "response_item",
            "payload": {
                "type": "custom_tool_call_output",
                "call_id": "call_image_exec",
                "output": [{"type": "input_text", "text": "Script completed\nOutput:\n"}],
            },
        },
        {
            "type": "event_msg",
            "payload": {
                "type": "image_generation_end",
                "status": "completed",
                "call_id": call_id,
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
            "payload": {
                "type": "task_complete",
                "turn_id": turn_id,
                "last_agent_message": None,
            },
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
                "thread_spawn": {
                    "parent_thread_id": parent_id,
                    "agent_path": agent_path,
                }
            }
        }
    )
    connection.execute(
        "INSERT INTO threads VALUES (?, ?, ?, ?, ?)",
        (thread_id, str(rollout), checkpoint // 1000 + 1, checkpoint + 1, source),
    )
    connection.commit()
    connection.close()

    copy_to = base / "attempts" / "01" / "board.png"
    result_json = base / "attempts" / "01" / "worker_result.json"
    command = [
        sys.executable,
        "-X",
        "utf8",
        str(RESOLVER),
        "--agent-path",
        agent_path,
        "--not-before-ms",
        str(checkpoint),
        "--parent-thread-id",
        parent_id,
        "--worker-run-nonce",
        nonce,
        "--expected-prompt",
        str(prompt_path),
    ]
    if mode == "manifest":
        command.extend(["--reference-manifest", str(manifest)])
    elif mode == "explicit":
        for reference in references:
            command.extend(["--expected-reference", str(reference)])
    else:
        command.extend(["--expected-recent-image-count", "2"])
    command.extend(
        [
            "--copy-to",
            str(copy_to),
            "--result-json",
            str(result_json),
            "--state-db",
            str(state_db),
            "--codex-home",
            str(codex_home),
        ]
    )
    return {
        "mode": mode,
        "agent_path": agent_path,
        "parent_id": parent_id,
        "thread_id": thread_id,
        "turn_id": turn_id,
        "call_id": call_id,
        "nonce": nonce,
        "checkpoint": checkpoint,
        "prompt": prompt,
        "prompt_path": prompt_path,
        "references": references,
        "manifest": manifest,
        "source_image": source_image,
        "rollout": rollout,
        "events": events,
        "state_db": state_db,
        "codex_home": codex_home,
        "copy_to": copy_to,
        "result_json": result_json,
        "command": command,
        "source": source,
    }


def run_fixture(fixture: dict[str, Any]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        fixture["command"],
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
        return payload.get("error_code")
    return None


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8", newline="\n")


def build_publication_fixture(base: Path) -> dict[str, Any]:
    run = base / "run"
    attempt = run / "attempts" / "01"
    attempt.mkdir(parents=True)
    generation = attempt / "asset_01_generation_prompt.md"
    enhancement = attempt / "asset_01_4k_enhancement_prompt.md"
    board = attempt / "board.png"
    worker = attempt / "worker_result.json"
    inspection = attempt / "qa.json"
    handoff = attempt / "4k_handoff.yaml"
    accepted_path = run / "accepted_attempt.json"
    manifest = run / "sources" / "reference-manifest.json"
    manifest.parent.mkdir(parents=True)
    output = run / "final_main_result.md"
    generation.write_bytes(b"Generate the accepted material board.")
    enhancement.write_bytes(b"Enhance only the inspected material board.")
    board.write_bytes(png_bytes())
    handoff.write_text(
        'aspect_ratio: "16:9"\n'
        'image_size: "4K"\n'
        f'codex_asset_board: "{board}"\n'
        'original_source_references:\n  - "source_01"\n',
        encoding="utf-8",
        newline="\n",
    )
    write_json(manifest, {"schema_version": "material_reference_bundle.v1"})
    generation_sha = hashlib.sha256(generation.read_bytes()).hexdigest()
    enhancement_sha = hashlib.sha256(enhancement.read_bytes()).hexdigest()
    board_sha = hashlib.sha256(board.read_bytes()).hexdigest()
    write_json(
        worker,
        {
            "ok": True,
            "contract": "delegated_product_image_worker_result.v1",
            "prompt_sha_match": True,
            "reference_mode": "frozen_manifest",
            "reference_bytes_verified": True,
            "reference_count": 2,
            "generation_prompt_sha256": generation_sha,
            "tool_prompt_sha256": generation_sha,
            "image_sha256": board_sha,
            "reference_manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
            "run_image_path": str(board),
            "worker_thread_id": "019f0000-0000-7000-8000-000000000002",
            "image_generation_call_id": "exec-11111111-2222-4333-8444-555555555555",
            "width_px": 1672,
            "height_px": 941,
        },
    )
    write_json(
        inspection,
        {
            "inspected": True,
            "attempt_id": "01",
            "assistant_qa_status": "passed",
            "image_sha256": board_sha,
            "prompt_bound": "pass",
            "single_board_contract": "pass",
            "material_evidence_present": "pass",
            "board_path": str(board),
            "production_approval_status": "not_granted",
        },
    )
    accepted = {
        "schema_version": "material_accepted_attempt.v1",
        "attempt_id": "01",
        "generation_prompt_path": str(generation),
        "enhancement_prompt_path": str(enhancement),
        "board_path": str(board),
        "worker_result_path": str(worker),
        "inspection_path": str(inspection),
        "handoff_path": str(handoff),
        "generation_prompt_sha256": generation_sha,
        "4k_enhancement_prompt_sha256": enhancement_sha,
        "image_sha256": board_sha,
        "worker_result_sha256": hashlib.sha256(worker.read_bytes()).hexdigest(),
        "inspection_sha256": hashlib.sha256(inspection.read_bytes()).hexdigest(),
        "handoff_sha256": hashlib.sha256(handoff.read_bytes()).hexdigest(),
    }
    write_json(accepted_path, accepted)
    command = [
        sys.executable,
        "-X",
        "utf8",
        str(FINAL_BUILDER),
        "--run-dir",
        str(run),
        "--accepted-attempt",
        str(accepted_path),
        "--board",
        str(board),
        "--generation-prompt",
        str(generation),
        "--enhancement-prompt",
        str(enhancement),
        "--worker-result",
        str(worker),
        "--inspection",
        str(inspection),
        "--reference-manifest",
        str(manifest),
        "--handoff",
        str(handoff),
        "--output",
        str(output),
    ]
    return {
        "run": run,
        "attempt": attempt,
        "accepted": accepted,
        "accepted_path": accepted_path,
        "generation": generation,
        "output": output,
        "command": command,
    }


def image_call_event(fixture: dict[str, Any]) -> dict[str, Any]:
    return next(
        event
        for event in fixture["events"]
        if event.get("type") == "response_item"
        and event.get("payload", {}).get("type") == "custom_tool_call"
    )


class ResolverContractTests(unittest.TestCase):
    def test_encrypted_task_envelope_without_user_message_is_green(self) -> None:
        with tempfile.TemporaryDirectory(prefix="material-resolver-encrypted-envelope-") as temp:
            fixture = build_fixture(Path(temp), "explicit")
            fixture["events"] = [
                event
                for event in fixture["events"]
                if not (
                    event.get("type") == "event_msg"
                    and event.get("payload", {}).get("type") == "user_message"
                )
            ]
            write_events(fixture["rollout"], fixture["events"])
            result = run_fixture(fixture)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_wrong_exec_nonce_is_red(self) -> None:
        with tempfile.TemporaryDirectory(prefix="material-resolver-nonce-") as temp:
            fixture = build_fixture(Path(temp), "explicit")
            image_call_event(fixture)["payload"]["input"] = image_call_input(
                fixture["prompt"],
                references=fixture["references"],
                nonce="f" * 32,
            )
            write_events(fixture["rollout"], fixture["events"])
            result = run_fixture(fixture)
            self.assertEqual(error_code(result), "blocked_worker_nonce_mismatch")

    def test_final_builder_publishes_only_accepted_attempt_pair(self) -> None:
        with tempfile.TemporaryDirectory(prefix="material-publication-") as temp:
            fixture = build_publication_fixture(Path(temp))
            result = subprocess.run(
                fixture["command"], capture_output=True, text=True, encoding="utf-8"
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            final = fixture["output"].read_text(encoding="utf-8")
            self.assertIn("final_generation_prompt:\nGenerate the accepted material board.", final)
            self.assertIn("final_4k_enhancement_prompt:\nEnhance only the inspected material board.", final)
            self.assertIn("main_result_prompt_pair_status: published", final)

    def test_final_builder_rejects_flat_prompt_outside_accepted_attempt(self) -> None:
        with tempfile.TemporaryDirectory(prefix="material-publication-flat-") as temp:
            fixture = build_publication_fixture(Path(temp))
            flat = fixture["run"] / "generation_prompt.md"
            flat.write_bytes(fixture["generation"].read_bytes())
            command = list(fixture["command"])
            index = command.index("--generation-prompt") + 1
            command[index] = str(flat)
            fixture["accepted"]["generation_prompt_path"] = str(flat)
            write_json(fixture["accepted_path"], fixture["accepted"])
            result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(error_code(result), "blocked_accepted_attempt_mismatch")

    def test_explicit_reference_success_binds_prompt_thread_call_and_png(self) -> None:
        with tempfile.TemporaryDirectory(prefix="material-resolver-explicit-") as temp:
            fixture = build_fixture(Path(temp), "explicit")
            result = run_fixture(fixture)
            self.assertEqual(result.returncode, 0, result.stderr)
            record = json.loads(fixture["result_json"].read_text(encoding="utf-8"))
            self.assertTrue(record["ok"])
            self.assertEqual(record["worker_thread_id"], fixture["thread_id"])
            self.assertEqual(record["image_generation_call_id"], fixture["call_id"])
            self.assertEqual(record["reference_mode"], "explicit_paths")
            self.assertEqual(record["reference_count"], 2)
            self.assertTrue(record["prompt_sha_match"])
            self.assertEqual(record["width_px"], 1672)
            self.assertEqual(record["height_px"], 941)
            self.assertEqual(fixture["copy_to"].read_bytes(), fixture["source_image"].read_bytes())

    def test_material_manifest_success_rehashes_frozen_references(self) -> None:
        with tempfile.TemporaryDirectory(prefix="material-resolver-manifest-") as temp:
            fixture = build_fixture(Path(temp), "manifest")
            result = run_fixture(fixture)
            self.assertEqual(result.returncode, 0, result.stderr)
            record = json.loads(fixture["result_json"].read_text(encoding="utf-8"))
            manifest_bytes = fixture["manifest"].read_bytes()
            self.assertEqual(record["reference_mode"], "frozen_manifest")
            self.assertEqual(record["reference_manifest_sha256"], hashlib.sha256(manifest_bytes).hexdigest())
            self.assertRegex(record["ordered_reference_bundle_sha256"], r"^[0-9a-f]{64}$")

    def test_recent_image_count_is_rejected_without_byte_identity(self) -> None:
        with tempfile.TemporaryDirectory(prefix="material-resolver-recent-") as temp:
            fixture = build_fixture(Path(temp), "recent")
            result = run_fixture(fixture)
            self.assertEqual(error_code(result), "blocked_worker_reference_contract_invalid")

    def test_shell_wrapper_prompt_mismatch_is_red(self) -> None:
        with tempfile.TemporaryDirectory(prefix="material-resolver-wrapper-") as temp:
            fixture = build_fixture(Path(temp), "explicit")
            wrapped = "Script completed\nWall time: 0.1 seconds\n" + fixture["prompt"]
            image_call_event(fixture)["payload"]["input"] = image_call_input(
                wrapped,
                references=fixture["references"],
            )
            write_events(fixture["rollout"], fixture["events"])
            result = run_fixture(fixture)
            self.assertEqual(error_code(result), "blocked_worker_prompt_mismatch")

    def test_decoy_prompt_key_cannot_mask_actual_call_mismatch(self) -> None:
        with tempfile.TemporaryDirectory(prefix="material-resolver-decoy-") as temp:
            fixture = build_fixture(Path(temp), "explicit")
            actual_call = image_call_input("wrong prompt", references=fixture["references"])
            image_call_event(fixture)["payload"]["input"] = (
                "const decoy = "
                + json.dumps({"prompt": fixture["prompt"]}, ensure_ascii=False)
                + ";\n"
                + actual_call
            )
            write_events(fixture["rollout"], fixture["events"])
            result = run_fixture(fixture)
            self.assertEqual(error_code(result), "blocked_worker_prompt_mismatch")

    def test_ambiguous_fresh_worker_is_red(self) -> None:
        with tempfile.TemporaryDirectory(prefix="material-resolver-ambiguous-") as temp:
            fixture = build_fixture(Path(temp), "explicit")
            connection = sqlite3.connect(fixture["state_db"])
            connection.execute(
                "INSERT INTO threads VALUES (?, ?, ?, ?, ?)",
                (
                    "019f0000-0000-7000-8000-000000000099",
                    str(fixture["rollout"]),
                    fixture["checkpoint"] // 1000 + 2,
                    fixture["checkpoint"] + 2,
                    fixture["source"],
                ),
            )
            connection.commit()
            connection.close()
            result = run_fixture(fixture)
            self.assertEqual(error_code(result), "blocked_worker_thread_ambiguous")

    def test_wrong_reference_order_is_red(self) -> None:
        with tempfile.TemporaryDirectory(prefix="material-resolver-reference-") as temp:
            fixture = build_fixture(Path(temp), "explicit")
            image_call_event(fixture)["payload"]["input"] = image_call_input(
                fixture["prompt"],
                references=list(reversed(fixture["references"])),
            )
            write_events(fixture["rollout"], fixture["events"])
            result = run_fixture(fixture)
            self.assertEqual(error_code(result), "blocked_worker_reference_mismatch")

    def test_any_recent_image_count_is_red(self) -> None:
        with tempfile.TemporaryDirectory(prefix="material-resolver-recent-count-") as temp:
            fixture = build_fixture(Path(temp), "recent")
            image_call_event(fixture)["payload"]["input"] = image_call_input(
                fixture["prompt"],
                recent_count=1,
            )
            write_events(fixture["rollout"], fixture["events"])
            result = run_fixture(fixture)
            self.assertEqual(error_code(result), "blocked_worker_reference_contract_invalid")

    def test_multiple_image_calls_are_red(self) -> None:
        with tempfile.TemporaryDirectory(prefix="material-resolver-multiple-") as temp:
            fixture = build_fixture(Path(temp), "explicit")
            duplicate = json.loads(json.dumps(image_call_event(fixture)))
            fixture["events"].insert(5, duplicate)
            write_events(fixture["rollout"], fixture["events"])
            result = run_fixture(fixture)
            self.assertEqual(error_code(result), "blocked_worker_image_call_count")

    def test_non_image_tool_call_after_generation_is_red(self) -> None:
        with tempfile.TemporaryDirectory(prefix="material-resolver-extra-tool-") as temp:
            fixture = build_fixture(Path(temp), "explicit")
            fixture["events"].insert(
                7,
                {
                    "type": "response_item",
                    "payload": {
                        "type": "custom_tool_call",
                        "name": "exec",
                        "input": "await tools.view_image({path: 'unexpected.png'});",
                    },
                },
            )
            write_events(fixture["rollout"], fixture["events"])
            result = run_fixture(fixture)
            self.assertEqual(error_code(result), "blocked_worker_unexpected_tool_call")

    def test_waits_bound_to_yielded_imagegen_cell_are_green(self) -> None:
        with tempfile.TemporaryDirectory(prefix="material-resolver-wait-") as temp:
            fixture = build_fixture(Path(temp), "explicit")
            output = fixture["events"].pop(5)
            output["payload"]["output"] = "Script running with cell ID 8\n"
            fixture["events"].insert(5, output)
            fixture["events"].insert(
                6,
                {
                    "type": "response_item",
                    "payload": {
                        "type": "function_call",
                        "name": "wait",
                        "call_id": "call_wait_1",
                        "arguments": json.dumps({"cell_id": "8", "yield_time_ms": 10000}),
                    },
                },
            )
            fixture["events"].insert(
                8,
                {
                    "type": "response_item",
                    "payload": {
                        "type": "function_call_output",
                        "call_id": "call_wait_1",
                        "output": "Script completed\nOutput:\n",
                    },
                },
            )
            write_events(fixture["rollout"], fixture["events"])
            result = run_fixture(fixture)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_wait_for_unrelated_cell_is_red(self) -> None:
        with tempfile.TemporaryDirectory(prefix="material-resolver-wrong-wait-") as temp:
            fixture = build_fixture(Path(temp), "explicit")
            output = fixture["events"].pop(5)
            output["payload"]["output"] = "Script running with cell ID 8\n"
            fixture["events"].insert(5, output)
            fixture["events"].insert(
                6,
                {
                    "type": "response_item",
                    "payload": {
                        "type": "function_call",
                        "name": "wait",
                        "call_id": "call_wait_bad",
                        "arguments": json.dumps({"cell_id": "9"}),
                    },
                },
            )
            fixture["events"].insert(
                8,
                {
                    "type": "response_item",
                    "payload": {
                        "type": "function_call_output",
                        "call_id": "call_wait_bad",
                        "output": "Script completed\n",
                    },
                },
            )
            write_events(fixture["rollout"], fixture["events"])
            result = run_fixture(fixture)
            self.assertEqual(error_code(result), "blocked_worker_wait_mismatch")

    def test_missing_thread_call_derived_png_is_red(self) -> None:
        with tempfile.TemporaryDirectory(prefix="material-resolver-missing-png-") as temp:
            fixture = build_fixture(Path(temp), "explicit")
            fixture["source_image"].unlink()
            result = run_fixture(fixture)
            self.assertEqual(error_code(result), "blocked_worker_image_missing")

    def test_saved_path_not_derived_from_thread_and_call_is_red(self) -> None:
        with tempfile.TemporaryDirectory(prefix="material-resolver-path-") as temp:
            fixture = build_fixture(Path(temp), "explicit")
            wrong = Path(temp) / "newest.png"
            wrong.write_bytes(png_bytes())
            next(
                event
                for event in fixture["events"]
                if event.get("type") == "event_msg"
                and event.get("payload", {}).get("type") == "image_generation_end"
            )["payload"]["saved_path"] = str(wrong)
            write_events(fixture["rollout"], fixture["events"])
            result = run_fixture(fixture)
            self.assertEqual(error_code(result), "blocked_worker_image_path_mismatch")

    def test_path_traversal_call_id_is_red(self) -> None:
        with tempfile.TemporaryDirectory(prefix="material-resolver-traversal-") as temp:
            fixture = build_fixture(Path(temp), "explicit")
            next(
                event
                for event in fixture["events"]
                if event.get("type") == "event_msg"
                and event.get("payload", {}).get("type") == "image_generation_end"
            )["payload"]["call_id"] = "exec-..\\..\\escape"
            write_events(fixture["rollout"], fixture["events"])
            result = run_fixture(fixture)
            self.assertEqual(error_code(result), "blocked_worker_image_event_incomplete")

    def test_wrong_manifest_schema_is_red(self) -> None:
        with tempfile.TemporaryDirectory(prefix="material-resolver-schema-") as temp:
            fixture = build_fixture(Path(temp), "manifest")
            manifest = json.loads(fixture["manifest"].read_text(encoding="utf-8"))
            manifest["schema_version"] = "single_face_reference_bundle.v1"
            fixture["manifest"].write_text(
                json.dumps(manifest, indent=2) + "\n",
                encoding="utf-8",
                newline="\n",
            )
            result = run_fixture(fixture)
            self.assertEqual(error_code(result), "blocked_worker_reference_manifest_invalid")


if __name__ == "__main__":
    unittest.main(verbosity=2)
