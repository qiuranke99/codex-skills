#!/usr/bin/env python3
"""Contract tests for the sparse-reference packaging video asset board."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

from PIL import Image


SCRIPT_DIR = Path(__file__).resolve().parent
PACKAGE_DIR = SCRIPT_DIR.parent
FREEZER = SCRIPT_DIR / "freeze_reference_bundle.py"
REFERENCE_PACKER = SCRIPT_DIR / "build_generation_reference_pack.py"
DISPATCH_VALIDATOR = SCRIPT_DIR / "validate_prompt_dispatch_trace.py"
COMPOSER = SCRIPT_DIR / "compose_asset_board.py"
VALIDATOR = SCRIPT_DIR / "validate_asset_board_run.py"
RESOLVER = SCRIPT_DIR / "resolve_worker_image.py"
COPY_COMPILER = SCRIPT_DIR / "compile_copy_prompt.py"
COPY_VALIDATOR = SCRIPT_DIR / "validate_copy_contract.py"
PROMPT_RENDERER = SCRIPT_DIR / "render_generation_prompt.py"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, encoding="utf-8")


def error_code(result: subprocess.CompletedProcess[str]) -> str | None:
    for line in reversed(result.stderr.splitlines()):
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        return value.get("error_code")
    return None


def make_image(path: Path, size: tuple[int, int], color: tuple[int, int, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color).save(path, format="PNG")


def generation_reference_fixture(base: Path, count: int = 7) -> dict[str, Any]:
    run_dir = base / "dispatch-run"
    inputs = base / "dispatch-inputs"
    originals: list[Path] = []
    for index in range(count):
        path = inputs / f"source-{index + 1:02d}.png"
        make_image(path, (720 + index * 7, 960 + index * 5), (180 + index * 5, 120 + index * 4, 60))
        originals.append(path)
    reference_manifest = run_dir / "reference-manifest.json"
    command = [
        sys.executable,
        "-X",
        "utf8",
        str(FREEZER),
        "--run-dir",
        str(run_dir),
        "--manifest",
        str(reference_manifest),
    ]
    for index, path in enumerate(originals, 1):
        alias = ["front", "back", "three_quarter"][index - 1] if index <= 3 else f"detail_{index - 3}"
        command.extend(["--reference", f"{alias}={path}"])
    frozen = run(command)
    if frozen.returncode != 0:
        raise AssertionError(frozen.stderr)
    output_dir = run_dir / "attempts" / "01" / "provider-references"
    pack_manifest = output_dir / "generation-reference-pack.json"
    packed = run(
        [
            sys.executable,
            "-X",
            "utf8",
            str(REFERENCE_PACKER),
            "--reference-manifest",
            str(reference_manifest),
            "--output-dir",
            str(output_dir),
            "--manifest",
            str(pack_manifest),
        ]
    )
    if packed.returncode != 0:
        raise AssertionError(packed.stderr)
    return {
        "run_dir": run_dir,
        "reference_manifest": reference_manifest,
        "pack_manifest": pack_manifest,
        "pack": json.loads(pack_manifest.read_text(encoding="utf-8")),
    }


def update_timeline(start: int, end: int) -> list[int]:
    values = list(range(start, end, 60_000))
    if not values or values[-1] != end:
        values.append(end)
    return values


def dispatch_trace_fixture(base: Path, terminal_status: str = "ACCEPTED") -> dict[str, Any]:
    references = generation_reference_fixture(base, 7)
    prompt = references["run_dir"] / "attempts" / "01" / "final_generation_prompt.md"
    prompt.write_text(
        "Create one fully populated nine-region borderless packaging board from exactly five ordered references.\n",
        encoding="utf-8",
        newline="\n",
    )
    prompt_elapsed = 70_000
    worker: dict[str, Any] = {
        "spawned_elapsed_ms": 80_000,
        "fork_turns": "none",
        "task_mentions_skill": False,
        "first_tool": "imagegen",
        "pre_imagegen_tool_call_count": 0,
        "reran_release_gate": False,
        "imagegen_submitted_elapsed_ms": 90_000,
        "imagegen_tool_call_count": 1,
        "imagegen_reference_count": 5,
        "retry_started_while_call_unknown": False,
    }
    if terminal_status == "ACCEPTED":
        terminal_elapsed = 330_000
        worker.update(
            {
                "image_ready_elapsed_ms": 250_000,
                "raw_preview_published_elapsed_ms": 270_000,
                "image_generation_end_count": 1,
                "bound_png": True,
                "success_claimed_elapsed_ms": 300_000,
            }
        )
        automatic_elapsed = 310_000
    elif terminal_status == "BLOCKED_IMAGEGEN_TIMEOUT":
        terminal_elapsed = 990_000
        automatic_elapsed = 920_000
    else:
        raise AssertionError(f"unsupported test status: {terminal_status}")
    value = {
        "schema_version": "packaging_prompt_dispatch_trace.v1",
        "run_id": "dispatch-fixture",
        "release_gate_completed_elapsed_ms": 20_000,
        "generation_prompt_path": str(prompt),
        "generation_prompt_sha256": sha(prompt),
        "generation_reference_pack_path": str(references["pack_manifest"]),
        "generation_reference_pack_sha256": sha(references["pack_manifest"]),
        "prompt_publication": {
            "mode": "inline_complete_prompt",
            "elapsed_ms": prompt_elapsed,
            "published_sha256": sha(prompt),
        },
        "worker": worker,
        "user_visible_update_elapsed_ms": update_timeline(prompt_elapsed, terminal_elapsed),
        "automatic_generation_elapsed_ms": automatic_elapsed,
        "terminal_status": terminal_status,
        "terminal_elapsed_ms": terminal_elapsed,
        "terminal_prompt_publication": {
            "mode": "inline_complete_prompt",
            "published_sha256": sha(prompt),
        },
    }
    trace = references["run_dir"] / "prompt-dispatch-trace.json"
    write_json(trace, value)
    return {"trace": trace, "value": value, **references}


def load_resolver_module():
    spec = importlib.util.spec_from_file_location("packaging_worker_resolver_test", RESOLVER)
    if spec is None or spec.loader is None:
        raise AssertionError("cannot load packaging worker resolver")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def worker_events(prompt: str, references: list[Path], nonce: str) -> dict[str, Any]:
    thread_id = "019f0000-0000-7000-8000-000000000001"
    parent_id = "019f0000-0000-7000-8000-000000000000"
    turn_id = "019f0000-0000-7000-8000-000000000010"
    agent_path = f"/root/packaging_image_test_{nonce}"
    reference_json = json.dumps([str(path) for path in references], ensure_ascii=False)
    prompt_json = json.dumps(prompt, ensure_ascii=False)
    call = {
        "type": "response_item",
        "payload": {
            "type": "custom_tool_call",
            "input": (
                f"const result = await tools.image_gen__imagegen({{prompt:{prompt_json},"
                f"referenced_image_paths:{reference_json}}}); generatedImage(result);"
            ),
        },
    }
    events = [
        {
            "type": "session_meta",
            "payload": {"id": thread_id, "agent_path": agent_path, "parent_thread_id": parent_id},
        },
        {"type": "event_msg", "payload": {"type": "task_started", "turn_id": turn_id}},
        {"type": "turn_context", "payload": {"turn_id": turn_id}},
        call,
        {
            "type": "event_msg",
            "payload": {
                "type": "image_generation_end",
                "revised_prompt": prompt,
                "status": "completed",
                "call_id": "image-call-001",
                "saved_path": "C:/generated/image-call-001.png",
            },
        },
        {"type": "event_msg", "payload": {"type": "agent_message", "phase": "final_answer", "message": ""}},
        {"type": "response_item", "payload": {"type": "message", "role": "assistant", "content": []}},
        {
            "type": "event_msg",
            "payload": {"type": "task_complete", "turn_id": turn_id, "last_agent_message": ""},
        },
    ]
    return {
        "events": events,
        "call": call,
        "thread_id": thread_id,
        "parent_id": parent_id,
        "agent_path": agent_path,
        "turn_id": turn_id,
    }


def valid_fixture(base: Path) -> dict[str, Any]:
    run_dir = base / "run"
    attempt = run_dir / "attempts" / "01"
    attempt.mkdir(parents=True)
    originals = [base / "inputs" / name for name in ["front.png", "back.png", "three-quarter.png"]]
    for path, color in zip(originals, [(238, 170, 70), (225, 150, 55), (245, 185, 80)]):
        make_image(path, (800, 1200), color)

    reference_manifest = run_dir / "reference-manifest.json"
    freeze_command = [
        sys.executable,
        "-X",
        "utf8",
        str(FREEZER),
        "--run-dir",
        str(run_dir),
        "--manifest",
        str(reference_manifest),
    ]
    for alias, path in zip(["front", "back", "three_quarter"], originals):
        freeze_command.extend(["--reference", f"{alias}={path}"])
    frozen = run(freeze_command)
    if frozen.returncode != 0:
        raise AssertionError(frozen.stderr)
    references = json.loads(reference_manifest.read_text(encoding="utf-8"))
    frozen_paths = {entry["alias"]: Path(entry["frozen_path"]) for entry in references["ordered_references"]}

    copy_ledger = run_dir / "copy-ledger.json"
    write_json(
        copy_ledger,
        {
            "schema_version": "packaging_copy_ledger.v1",
            "product_id": "fixture-product",
            "ocr_status": "candidates_only",
            "regions": [
                {
                    "region_id": "front_label",
                    "surface": "front",
                    "source_alias": "front",
                    "source_sha256": sha(frozen_paths["front"]),
                    "layout": {
                        "orientation": "upright",
                        "reading_order": "top-to-bottom",
                        "column_order": "single-column",
                        "alignment": "center",
                    },
                    "lines": [
                        {
                            "line_id": "front_label.L001",
                            "order": 1,
                            "text": "GAAR",
                            "language": "en",
                            "status": "approved_exact",
                            "evidence": "source_visual",
                        },
                        {
                            "line_id": "front_label.L002",
                            "order": 2,
                            "text": "unreadable supporting copy",
                            "language": "und",
                            "status": "unresolved",
                            "evidence": "not_readable",
                        },
                    ],
                }
            ],
        },
    )
    copy_block = attempt / "copy-prompt-block.md"
    copy_receipt = attempt / "copy-prompt-receipt.json"
    compiled = run(
        [
            sys.executable,
            "-X",
            "utf8",
            str(COPY_COMPILER),
            "--ledger",
            str(copy_ledger),
            "--output",
            str(copy_block),
            "--receipt",
            str(copy_receipt),
        ]
    )
    if compiled.returncode != 0:
        raise AssertionError(compiled.stderr)

    prompt = attempt / "final_generation_prompt.md"
    prompt_values = attempt / "generation-prompt-values.json"
    values = json.loads((PACKAGE_DIR / "references" / "generation_prompt_values.template.json").read_text(encoding="utf-8"))
    write_json(prompt_values, values)
    prompt_receipt = attempt / "generation-prompt-receipt.json"
    rendered = run(
        [
            sys.executable,
            "-X",
            "utf8",
            str(PROMPT_RENDERER),
            "--template",
            str(PACKAGE_DIR / "references" / "generation_prompt_template.md"),
            "--values",
            str(prompt_values),
            "--copy-block",
            str(copy_block),
            "--output",
            str(prompt),
            "--receipt",
            str(prompt_receipt),
        ]
    )
    if rendered.returncode != 0:
        raise AssertionError(rendered.stderr)
    copy_qa = attempt / "copy-qa.json"
    write_json(
        copy_qa,
        {
            "schema_version": "packaging_copy_qa.v1",
            "copy_ledger_sha256": sha(copy_ledger),
            "copy_prompt_block_sha256": sha(copy_block),
            "overall_status": "passed",
            "board_wide_invented_or_corrupted_visible_copy": False,
            "board_regions": [
                {
                    "board_region_id": "local_identity_detail",
                    "visual_status": "source_reprojected",
                    "covered_copy_region_ids": ["front_label"],
                    "order_match": "pass",
                    "source_backed_pixels": True,
                    "mismatch_line_ids": [],
                }
            ],
        },
    )
    raw = attempt / "raw-board.png"
    make_image(raw, (1600, 900), (246, 246, 246))
    worker = attempt / "worker-result.json"
    worker_value = {
        "ok": True,
        "contract": "delegated_image_worker_result.v1",
        "prompt_sha_match": True,
        "reference_bytes_verified": True,
        "generation_prompt_sha256": sha(prompt),
        "tool_prompt_sha256": sha(prompt),
        "reference_manifest_sha256": sha(reference_manifest),
        "reference_count": 3,
        "image_sha256": sha(raw),
        "run_image_path": str(raw),
    }
    write_json(worker, worker_value)

    plan = attempt / "composition-plan.json"
    overlays: list[dict[str, Any]] = []
    overlays.append(
        {
            "region_id": "front_anchor",
            "role": "anchor",
            "source_path": str(frozen_paths["front"]),
            "source_sha256": sha(frozen_paths["front"]),
            "crop_box": [0, 0, 800, 1200],
            "target_box": [0, 0, 720, 1500],
            "fit": "contain",
            "seamless_background_match": True,
            "border_px": 0,
        }
    )
    detail_aliases = ["three_quarter", "front"]
    detail_ids = ["closure_top", "local_identity_detail"]
    for index, alias in enumerate(detail_aliases):
        overlays.append(
            {
                "region_id": detail_ids[index],
                "role": "detail",
                "source_path": str(frozen_paths[alias]),
                "source_sha256": sha(frozen_paths[alias]),
                "crop_box": [100, 300, 700, 900],
                "target_box": [index * 1920, 1680, (index + 1) * 1920, 2160],
                "fit": "cover",
                "seamless_background_match": True,
                "border_px": 0,
            }
        )
    final_board = attempt / "final-board.png"
    write_json(
        plan,
        {
            "schema_version": "packaging_board_composition_plan.v2",
            "raw_board_path": str(raw),
            "raw_board_sha256": sha(raw),
            "output_board_path": str(final_board),
            "canvas_size": [3840, 2160],
            "base_fit": "cover",
            "layout_style": "borderless_continuous_background",
            "drawn_borders": False,
            "detail_layout": [
                {"region_id": detail_ids[index], "target_box": [index * 1920, 1680, (index + 1) * 1920, 2160]}
                for index in range(2)
            ],
            "overlays": overlays,
        },
    )
    receipt = attempt / "composition-receipt.json"
    composed = run(
        [
            sys.executable,
            "-X",
            "utf8",
            str(COMPOSER),
            "--run-dir",
            str(run_dir),
            "--plan",
            str(plan),
            "--receipt",
            str(receipt),
        ]
    )
    if composed.returncode != 0:
        raise AssertionError(composed.stderr)

    views = [
        {"view_id": "front", "evidence_status": "source_observed"},
        {"view_id": "back", "evidence_status": "source_observed"},
        {"view_id": "side", "evidence_status": "source_observed"},
        {"view_id": "high_side_45", "evidence_status": "bounded_inferred"},
        {"view_id": "low_side_45", "evidence_status": "bounded_inferred"},
        {"view_id": "top_down", "evidence_status": "bounded_inferred"},
        {"view_id": "low_up", "evidence_status": "bounded_inferred"},
    ]
    details = [
        {
            "region_id": detail_ids[index],
            "evidence_status": "deterministic_reprojection",
            "source_alias": alias,
        }
        for index, alias in enumerate(detail_aliases)
    ]
    manifest = run_dir / "asset-board-manifest.json"
    manifest_value = {
        "schema_version": "packaging_video_asset_board.v2",
        "run_status": "COMPLETE",
        "input_profile": "one_to_three_reference",
        "reference_manifest_path": str(reference_manifest),
        "copy_ledger_path": str(copy_ledger),
        "copy_ledger_sha256": sha(copy_ledger),
        "copy_prompt_block_path": str(copy_block),
        "copy_prompt_block_sha256": sha(copy_block),
        "copy_prompt_receipt_path": str(copy_receipt),
        "copy_prompt_receipt_sha256": sha(copy_receipt),
        "copy_qa_path": str(copy_qa),
        "copy_qa_sha256": sha(copy_qa),
        "generation_prompt_path": str(prompt),
        "generation_prompt_sha256": sha(prompt),
        "worker_result_path": str(worker),
        "worker_result_sha256": sha(worker),
        "composition_plan_path": str(plan),
        "composition_plan_sha256": sha(plan),
        "composition_receipt_path": str(receipt),
        "composition_receipt_sha256": sha(receipt),
        "final_board_path": str(final_board),
        "final_board_sha256": sha(final_board),
        "ocr": {"status": "candidates_only", "blocking": False},
        "copy_authority": "video_reference",
        "unresolved_regions": ["hidden_side_microcopy"],
        "layout_style": "borderless_continuous_background",
        "region_count": 9,
        "view_regions": views,
        "detail_regions": details,
        "qa": {
            "inspected": True,
            "seven_complete_views": "pass",
            "two_to_three_details": "pass",
            "nine_to_ten_total_regions": "pass",
            "borderless_continuous_background": "pass",
            "no_visible_frames": "pass",
            "identity_consistency": "pass",
            "label_fidelity": "pass",
            "copy_prompt_coverage": "pass",
            "copy_pixel_qa": "pass",
            "source_anchor_match": "pass",
            "non_product_text_pollution": "pass",
            "all_regions_populated": "pass",
            "assistant_qa_status": "conditional",
        },
    }
    write_json(manifest, manifest_value)
    return {
        "manifest": manifest,
        "value": manifest_value,
        "run_dir": run_dir,
        "plan": plan,
        "receipt": receipt,
        "worker": worker,
        "prompt": prompt,
        "reference_manifest": reference_manifest,
        "copy_ledger": copy_ledger,
        "copy_block": copy_block,
        "copy_receipt": copy_receipt,
        "copy_qa": copy_qa,
        "prompt_values": prompt_values,
        "prompt_receipt": prompt_receipt,
    }


class ContractTests(unittest.TestCase):
    def test_skill_declares_one_board_and_nonblocking_ocr(self) -> None:
        skill = (PACKAGE_DIR / "SKILL.md").read_text(encoding="utf-8")
        for token in [
            "exactly one clean horizontal 16:9 board",
            "exactly seven complete product views",
            "two source-grounded detail regions by default",
            "nine regions by default and never more than ten",
            "borderless_continuous_background",
            "compile_copy_prompt.py",
            "validate_copy_contract.py",
            "OCR remains nonblocking",
            "Do not make OCR completion a global gate",
            "never request a fixed 8/12/16/24-angle capture set",
            "The main agent must not call imagegen directly",
            "at most two repair attempts",
            "No blank cells, empty rectangles, placeholders, reserved slots",
            "independently usable as a final single-call prompt",
            "Publish the complete prompt text inline",
            "fork_turns=\"none\"",
            "imagegen may receive at most five paths",
            "at most 15 minutes",
            "unaccepted raw preview",
            "never spend another image call on that binding-only condition",
        ]:
            self.assertIn(token, skill)

    def test_prompt_template_is_standalone_and_population_safe(self) -> None:
        prompt = (PACKAGE_DIR / "references" / "generation_prompt_template.md").read_text(encoding="utf-8")
        for required in [
            "exactly {{detail_count}} source-grounded close-ups",
            "{{detail_region_list}}",
            "{{copy_contract_block}}",
            "No white frames, grid lines, panel outlines",
            "ten is the absolute maximum",
            "No blank cells, empty rectangles, placeholders, reserved slots",
            "independently usable",
            "Keep every product complete and upright on its base",
            "never submit more than five paths",
            "{{provider_reference_roles}}",
        ]:
            self.assertIn(required, prompt)
        for forbidden in [
            "will be replaced",
            "Keep those six windows visually empty",
            "Do not place any generated close-up content",
        ]:
            self.assertNotIn(forbidden, prompt)

    def test_seven_sources_compile_to_exactly_five_provider_references(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = generation_reference_fixture(Path(tmp), 7)
            pack = fixture["pack"]
            self.assertEqual(pack["source_reference_count"], 7)
            self.assertEqual(pack["provider_reference_count"], 5)
            self.assertEqual([row["role"] for row in pack["provider_references"][:3]], ["direct_anchor"] * 3)
            self.assertEqual([row["role"] for row in pack["provider_references"][3:]], ["detail_sheet"] * 2)
            self.assertEqual(
                [alias for row in pack["provider_references"] for alias in row["source_aliases"]],
                ["front", "back", "three_quarter", "detail_1", "detail_2", "detail_3", "detail_4"],
            )

    def test_three_sources_remain_three_direct_provider_references(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = generation_reference_fixture(Path(tmp), 3)
            self.assertEqual(fixture["pack"]["provider_reference_count"], 3)
            self.assertTrue(all(row["role"] == "direct_source" for row in fixture["pack"]["provider_references"]))

    def test_provider_reference_pack_is_resolver_compatible(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = generation_reference_fixture(Path(tmp), 7)
            resolver = load_resolver_module()
            evidence = resolver.load_reference_manifest(fixture["pack_manifest"])
            self.assertEqual(evidence["reference_count"], 5)
            self.assertEqual(evidence["reference_mode"], "generation_provider_pack")

    def test_resolver_rejects_more_than_one_imagegen_wrapper_call(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = generation_reference_fixture(Path(tmp), 3)
            resolver = load_resolver_module()
            reference_evidence = resolver.load_reference_manifest(fixture["pack_manifest"])
            nonce = "0123456789abcdef0123456789abcdef"
            prompt = "Create one complete packaging identity board."
            worker = worker_events(prompt, reference_evidence["paths"], nonce)
            duplicate = copy.deepcopy(worker["events"])
            duplicate.insert(4, copy.deepcopy(worker["call"]))
            with self.assertRaises(resolver.ContractError) as caught:
                resolver.validate_worker_rollout(
                    events=duplicate,
                    thread_id=worker["thread_id"],
                    agent_path=worker["agent_path"],
                    parent_thread_id=worker["parent_id"],
                    worker_run_nonce=nonce,
                    expected_prompt_bytes=prompt.encode("utf-8"),
                    expected_references=reference_evidence["paths"],
                    allow_no_references=False,
                )
            self.assertEqual(caught.exception.code, "blocked_worker_image_call_count")

    def test_resolver_accepts_exact_prompt_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = generation_reference_fixture(Path(tmp), 3)
            resolver = load_resolver_module()
            reference_evidence = resolver.load_reference_manifest(fixture["pack_manifest"])
            nonce = "0123456789abcdef0123456789abcdef"
            prompt = "Create one complete packaging identity board.\n"
            worker = worker_events(prompt, reference_evidence["paths"], nonce)
            evidence = resolver.validate_worker_rollout(
                events=worker["events"],
                thread_id=worker["thread_id"],
                agent_path=worker["agent_path"],
                parent_thread_id=worker["parent_id"],
                worker_run_nonce=nonce,
                expected_prompt_bytes=prompt.encode("utf-8"),
                expected_references=reference_evidence["paths"],
                allow_no_references=False,
            )
            self.assertTrue(evidence["prompt_sha_match"])
            self.assertTrue(evidence["prompt_content_match"])
            self.assertEqual(evidence["prompt_transport_mode"], "exact_bytes")
            self.assertFalse(evidence["prompt_transport_normalization_applied"])

    def test_resolver_accepts_only_one_omitted_file_terminal_lf(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = generation_reference_fixture(Path(tmp), 3)
            resolver = load_resolver_module()
            reference_evidence = resolver.load_reference_manifest(fixture["pack_manifest"])
            nonce = "0123456789abcdef0123456789abcdef"
            provider_prompt = "Create one complete packaging identity board."
            worker = worker_events(provider_prompt, reference_evidence["paths"], nonce)
            evidence = resolver.validate_worker_rollout(
                events=worker["events"],
                thread_id=worker["thread_id"],
                agent_path=worker["agent_path"],
                parent_thread_id=worker["parent_id"],
                worker_run_nonce=nonce,
                expected_prompt_bytes=(provider_prompt + "\n").encode("utf-8"),
                expected_references=reference_evidence["paths"],
                allow_no_references=False,
            )
            self.assertFalse(evidence["prompt_sha_match"])
            self.assertTrue(evidence["prompt_content_match"])
            self.assertEqual(evidence["prompt_transport_mode"], "single_terminal_lf_omitted")
            self.assertTrue(evidence["prompt_transport_normalization_applied"])
            self.assertEqual(evidence["prompt_content_sha256"], hashlib.sha256(provider_prompt.encode()).hexdigest())

    def test_resolver_rejects_prompt_body_or_internal_whitespace_changes(self) -> None:
        resolver = load_resolver_module()
        for expected, observed in [
            (b"Create the exact board.\n", "Create a different board."),
            (b"Create  the exact board.\n", "Create the exact board."),
            (b"Create the exact board.\n", "Create the exact board.\r\n"),
            (b"Create the exact board.\r\n", "Create the exact board.\r"),
        ]:
            with self.subTest(observed=repr(observed)):
                with self.assertRaises(resolver.ContractError) as caught:
                    resolver.bind_prompt_transport(expected, observed, "test prompt")
                self.assertEqual(caught.exception.code, "blocked_worker_prompt_mismatch")

    def test_resolver_rejects_more_than_one_terminal_newline_variance(self) -> None:
        resolver = load_resolver_module()
        with self.assertRaises(resolver.ContractError) as caught:
            resolver.bind_prompt_transport(b"Create the exact board.\n\n", "Create the exact board.\n", "test prompt")
        self.assertEqual(caught.exception.code, "blocked_worker_prompt_mismatch")

    def test_prompt_first_dispatch_accepts_a_bounded_success_trace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = dispatch_trace_fixture(Path(tmp))
            result = run([sys.executable, "-X", "utf8", str(DISPATCH_VALIDATOR), "--trace", str(fixture["trace"])])
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["provider_reference_count"], 5)

    def test_prompt_path_without_inline_publication_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = dispatch_trace_fixture(Path(tmp))
            value = copy.deepcopy(fixture["value"])
            value["prompt_publication"]["mode"] = "path_only"
            write_json(fixture["trace"], value)
            result = run([sys.executable, "-X", "utf8", str(DISPATCH_VALIDATOR), "--trace", str(fixture["trace"])])
            self.assertEqual(error_code(result), "blocked_prompt_not_inline")

    def test_worker_cannot_spawn_before_complete_prompt_publication(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = dispatch_trace_fixture(Path(tmp))
            value = copy.deepcopy(fixture["value"])
            value["worker"]["spawned_elapsed_ms"] = 60_000
            write_json(fixture["trace"], value)
            result = run([sys.executable, "-X", "utf8", str(DISPATCH_VALIDATOR), "--trace", str(fixture["trace"])])
            self.assertEqual(error_code(result), "blocked_worker_start_timeout")

    def test_worker_first_and_only_tool_must_be_imagegen(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = dispatch_trace_fixture(Path(tmp))
            value = copy.deepcopy(fixture["value"])
            value["worker"]["first_tool"] = "shell"
            value["worker"]["pre_imagegen_tool_call_count"] = 1
            write_json(fixture["trace"], value)
            result = run([sys.executable, "-X", "utf8", str(DISPATCH_VALIDATOR), "--trace", str(fixture["trace"])])
            self.assertEqual(error_code(result), "blocked_worker_first_tool")

    def test_worker_submission_after_ninety_seconds_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = dispatch_trace_fixture(Path(tmp))
            value = copy.deepcopy(fixture["value"])
            value["worker"]["imagegen_submitted_elapsed_ms"] = 180_001
            write_json(fixture["trace"], value)
            result = run([sys.executable, "-X", "utf8", str(DISPATCH_VALIDATOR), "--trace", str(fixture["trace"])])
            self.assertEqual(error_code(result), "blocked_worker_submit_timeout")

    def test_imagegen_timeout_still_requires_complete_prompt_and_no_orphan_retry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = dispatch_trace_fixture(Path(tmp), "BLOCKED_IMAGEGEN_TIMEOUT")
            result = run([sys.executable, "-X", "utf8", str(DISPATCH_VALIDATOR), "--trace", str(fixture["trace"])])
            self.assertEqual(result.returncode, 0, result.stderr)
            value = copy.deepcopy(fixture["value"])
            value["worker"]["retry_started_while_call_unknown"] = True
            write_json(fixture["trace"], value)
            retry = run([sys.executable, "-X", "utf8", str(DISPATCH_VALIDATOR), "--trace", str(fixture["trace"])])
            self.assertEqual(error_code(retry), "blocked_orphan_retry")

    def test_generation_success_cannot_be_claimed_before_image_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = dispatch_trace_fixture(Path(tmp))
            value = copy.deepcopy(fixture["value"])
            value["worker"]["success_claimed_elapsed_ms"] = 200_000
            write_json(fixture["trace"], value)
            result = run([sys.executable, "-X", "utf8", str(DISPATCH_VALIDATOR), "--trace", str(fixture["trace"])])
            self.assertEqual(error_code(result), "blocked_premature_success_claim")

    def test_three_references_validate_with_unresolved_microcopy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = valid_fixture(Path(tmp))
            result = run([sys.executable, "-X", "utf8", str(VALIDATOR), "--manifest", str(fixture["manifest"])])
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["reference_count"], 3)
            self.assertEqual(payload["view_count"], 7)
            self.assertEqual(payload["detail_count"], 2)
            self.assertEqual(payload["region_count"], 9)
            self.assertEqual(payload["copy_authority"], "video_reference")

    def test_provider_pack_worker_reference_binding_validates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = valid_fixture(Path(tmp))
            output_dir = fixture["run_dir"] / "attempts" / "01" / "provider-references"
            pack_manifest = output_dir / "generation-reference-pack.json"
            packed = run(
                [
                    sys.executable,
                    "-X",
                    "utf8",
                    str(REFERENCE_PACKER),
                    "--reference-manifest",
                    str(fixture["reference_manifest"]),
                    "--output-dir",
                    str(output_dir),
                    "--manifest",
                    str(pack_manifest),
                ]
            )
            self.assertEqual(packed.returncode, 0, packed.stderr)
            pack = json.loads(pack_manifest.read_text(encoding="utf-8"))
            prompt_bytes = fixture["prompt"].read_bytes()
            worker = json.loads(fixture["worker"].read_text(encoding="utf-8"))
            worker.update(
                {
                    "contract": "delegated_image_worker_result.v2",
                    "frozen_prompt_sha256": hashlib.sha256(prompt_bytes).hexdigest(),
                    "prompt_content_sha256": hashlib.sha256(prompt_bytes[:-1]).hexdigest(),
                    "prompt_content_match": True,
                    "prompt_transport_mode": "exact_bytes",
                    "prompt_transport_normalization_applied": False,
                    "reference_mode": "generation_provider_pack",
                    "reference_manifest_path": str(pack_manifest),
                    "reference_manifest_sha256": sha(pack_manifest),
                    "ordered_reference_bundle_sha256": pack["provider_bundle_sha256"],
                    "reference_count": pack["provider_reference_count"],
                }
            )
            write_json(fixture["worker"], worker)
            value = copy.deepcopy(fixture["value"])
            value["worker_result_sha256"] = sha(fixture["worker"])
            value["generation_reference_pack_path"] = str(pack_manifest)
            value["generation_reference_pack_sha256"] = sha(pack_manifest)
            write_json(fixture["manifest"], value)
            result = run([sys.executable, "-X", "utf8", str(VALIDATOR), "--manifest", str(fixture["manifest"])])
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_provider_pack_worker_reference_mismatch_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = valid_fixture(Path(tmp))
            worker = json.loads(fixture["worker"].read_text(encoding="utf-8"))
            worker["reference_mode"] = "generation_provider_pack"
            write_json(fixture["worker"], worker)
            value = copy.deepcopy(fixture["value"])
            value["worker_result_sha256"] = sha(fixture["worker"])
            write_json(fixture["manifest"], value)
            result = run([sys.executable, "-X", "utf8", str(VALIDATOR), "--manifest", str(fixture["manifest"])])
            self.assertEqual(error_code(result), "blocked_manifest_path_invalid")

    def test_missing_view_fails_without_requesting_more_sources(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = valid_fixture(Path(tmp))
            value = copy.deepcopy(fixture["value"])
            value["view_regions"].pop()
            write_json(fixture["manifest"], value)
            result = run([sys.executable, "-X", "utf8", str(VALIDATOR), "--manifest", str(fixture["manifest"])])
            self.assertEqual(result.returncode, 2)
            self.assertEqual(error_code(result), "blocked_view_coverage")

    def test_ocr_cannot_become_global_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = valid_fixture(Path(tmp))
            value = copy.deepcopy(fixture["value"])
            value["ocr"]["blocking"] = True
            write_json(fixture["manifest"], value)
            result = run([sys.executable, "-X", "utf8", str(VALIDATOR), "--manifest", str(fixture["manifest"])])
            self.assertEqual(result.returncode, 2)
            self.assertEqual(error_code(result), "blocked_ocr_global_gate")

    def test_exact_copy_authority_requires_review_and_no_unknowns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = valid_fixture(Path(tmp))
            value = copy.deepcopy(fixture["value"])
            value["copy_authority"] = "exact_copy_evidence"
            write_json(fixture["manifest"], value)
            result = run([sys.executable, "-X", "utf8", str(VALIDATOR), "--manifest", str(fixture["manifest"])])
            self.assertEqual(result.returncode, 2)
            self.assertEqual(error_code(result), "blocked_exact_copy_authority")

    def test_copy_compiler_emits_every_line_in_declared_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = valid_fixture(Path(tmp))
            block = fixture["copy_block"].read_text(encoding="utf-8")
            first = block.index('[front_label.L001] "GAAR"')
            second = block.index('[front_label.L002] status=unresolved candidate="unreadable supporting copy"')
            self.assertLess(first, second)
            receipt = json.loads(fixture["copy_receipt"].read_text(encoding="utf-8"))
            self.assertTrue(receipt["all_lines_emitted"])
            self.assertTrue(receipt["order_preserved"])
            self.assertEqual(receipt["line_count"], 2)
            prompt_receipt = json.loads(fixture["prompt_receipt"].read_text(encoding="utf-8"))
            self.assertTrue(prompt_receipt["copy_block_embedded_verbatim"])
            self.assertEqual(prompt_receipt["unresolved_placeholder_count"], 0)

    def test_ocr_only_text_cannot_be_approved_exact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = valid_fixture(Path(tmp))
            ledger = json.loads(fixture["copy_ledger"].read_text(encoding="utf-8"))
            ledger["regions"][0]["lines"][0]["evidence"] = "ocr_only"
            write_json(fixture["copy_ledger"], ledger)
            result = run(
                [
                    sys.executable,
                    "-X",
                    "utf8",
                    str(COPY_COMPILER),
                    "--ledger",
                    str(fixture["copy_ledger"]),
                    "--output",
                    str(fixture["copy_block"]),
                    "--receipt",
                    str(fixture["copy_receipt"]),
                ]
            )
            self.assertEqual(error_code(result), "blocked_copy_ledger_unverified_exact")

    def test_copy_ledger_must_bind_frozen_source_alias_and_hash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = valid_fixture(Path(tmp))
            ledger = json.loads(fixture["copy_ledger"].read_text(encoding="utf-8"))
            ledger["regions"][0]["source_sha256"] = "0" * 64
            write_json(fixture["copy_ledger"], ledger)
            value = copy.deepcopy(fixture["value"])
            value["copy_ledger_sha256"] = sha(fixture["copy_ledger"])
            write_json(fixture["manifest"], value)
            result = run([sys.executable, "-X", "utf8", str(VALIDATOR), "--manifest", str(fixture["manifest"])])
            self.assertEqual(error_code(result), "blocked_copy_ledger_source_binding")

    def test_prompt_missing_copy_block_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = valid_fixture(Path(tmp))
            fixture["prompt"].write_text("No copy block here.\n", encoding="utf-8", newline="\n")
            result = run(
                [
                    sys.executable,
                    "-X",
                    "utf8",
                    str(COPY_VALIDATOR),
                    "--ledger",
                    str(fixture["copy_ledger"]),
                    "--block",
                    str(fixture["copy_block"]),
                    "--receipt",
                    str(fixture["copy_receipt"]),
                    "--prompt",
                    str(fixture["prompt"]),
                    "--qa",
                    str(fixture["copy_qa"]),
                    "--copy-authority",
                    "video_reference",
                ]
            )
            self.assertEqual(error_code(result), "blocked_copy_prompt_coverage")

    def test_visible_gibberish_flag_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = valid_fixture(Path(tmp))
            qa = json.loads(fixture["copy_qa"].read_text(encoding="utf-8"))
            qa["board_wide_invented_or_corrupted_visible_copy"] = True
            write_json(fixture["copy_qa"], qa)
            result = run(
                [
                    sys.executable,
                    "-X",
                    "utf8",
                    str(COPY_VALIDATOR),
                    "--ledger",
                    str(fixture["copy_ledger"]),
                    "--block",
                    str(fixture["copy_block"]),
                    "--receipt",
                    str(fixture["copy_receipt"]),
                    "--prompt",
                    str(fixture["prompt"]),
                    "--qa",
                    str(fixture["copy_qa"]),
                    "--copy-authority",
                    "video_reference",
                ]
            )
            self.assertEqual(error_code(result), "blocked_visible_copy_corruption")

    def test_staging_prompt_leakage_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = valid_fixture(Path(tmp))
            prompt = fixture["run_dir"] / "attempts" / "01" / "final_generation_prompt.md"
            prompt.write_text(
                "Create a board. Reserve exactly six clean rectangular detail windows. "
                "Keep those six windows visually empty and neutral because they will be replaced after generation. "
                "Do not place any generated close-up content inside the six reserved detail windows.\n",
                encoding="utf-8",
                newline="\n",
            )
            value = copy.deepcopy(fixture["value"])
            value["generation_prompt_sha256"] = sha(prompt)
            write_json(fixture["manifest"], value)
            result = run([sys.executable, "-X", "utf8", str(VALIDATOR), "--manifest", str(fixture["manifest"])])
            self.assertEqual(result.returncode, 2)
            self.assertEqual(error_code(result), "blocked_staging_prompt_leakage")

    def test_overlapping_detail_layout_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = valid_fixture(Path(tmp))
            plan = json.loads(fixture["plan"].read_text(encoding="utf-8"))
            plan["detail_layout"][1]["target_box"] = copy.deepcopy(plan["detail_layout"][0]["target_box"])
            write_json(fixture["plan"], plan)
            result = run(
                [
                    sys.executable,
                    "-X",
                    "utf8",
                    str(COMPOSER),
                    "--run-dir",
                    str(fixture["run_dir"]),
                    "--plan",
                    str(fixture["plan"]),
                    "--receipt",
                    str(fixture["receipt"]),
                ]
            )
            self.assertEqual(result.returncode, 2)
            self.assertEqual(error_code(result), "blocked_composition_detail_layout_overlap")

    def test_missing_detail_overlay_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = valid_fixture(Path(tmp))
            plan = json.loads(fixture["plan"].read_text(encoding="utf-8"))
            plan["overlays"] = plan["overlays"][:-1]
            write_json(fixture["plan"], plan)
            result = run(
                [
                    sys.executable,
                    "-X",
                    "utf8",
                    str(COMPOSER),
                    "--run-dir",
                    str(fixture["run_dir"]),
                    "--plan",
                    str(fixture["plan"]),
                    "--receipt",
                    str(fixture["receipt"]),
                ]
            )
            self.assertEqual(result.returncode, 2)
            self.assertEqual(error_code(result), "blocked_composition_detail_mapping")

    def test_drawn_overlay_border_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = valid_fixture(Path(tmp))
            plan = json.loads(fixture["plan"].read_text(encoding="utf-8"))
            plan["overlays"][1]["border_px"] = 1
            write_json(fixture["plan"], plan)
            result = run(
                [
                    sys.executable,
                    "-X",
                    "utf8",
                    str(COMPOSER),
                    "--run-dir",
                    str(fixture["run_dir"]),
                    "--plan",
                    str(fixture["plan"]),
                    "--receipt",
                    str(fixture["receipt"]),
                ]
            )
            self.assertEqual(error_code(result), "blocked_composition_visible_frame")

    def test_near_blank_detail_crop_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = valid_fixture(Path(tmp))
            blank = fixture["run_dir"] / "references" / "blank.png"
            make_image(blank, (800, 1200), (248, 248, 248))
            plan = json.loads(fixture["plan"].read_text(encoding="utf-8"))
            detail = next(overlay for overlay in plan["overlays"] if overlay["role"] == "detail")
            detail["source_path"] = str(blank)
            detail["source_sha256"] = sha(blank)
            detail["crop_box"] = [0, 0, 800, 1200]
            write_json(fixture["plan"], plan)
            result = run(
                [
                    sys.executable,
                    "-X",
                    "utf8",
                    str(COMPOSER),
                    "--run-dir",
                    str(fixture["run_dir"]),
                    "--plan",
                    str(fixture["plan"]),
                    "--receipt",
                    str(fixture["receipt"]),
                ]
            )
            self.assertEqual(result.returncode, 2)
            self.assertEqual(error_code(result), "blocked_composition_detail_blank")

    def test_manifest_detail_mapping_mismatch_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = valid_fixture(Path(tmp))
            value = copy.deepcopy(fixture["value"])
            value["detail_regions"][0]["region_id"] = "unbound_detail"
            write_json(fixture["manifest"], value)
            result = run([sys.executable, "-X", "utf8", str(VALIDATOR), "--manifest", str(fixture["manifest"])])
            self.assertEqual(result.returncode, 2)
            self.assertEqual(error_code(result), "blocked_composition_detail_mapping")


if __name__ == "__main__":
    unittest.main(verbosity=2)
