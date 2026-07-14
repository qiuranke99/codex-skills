#!/usr/bin/env python3
"""Contract tests for the sparse-reference packaging video asset board."""

from __future__ import annotations

import copy
import hashlib
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
COMPOSER = SCRIPT_DIR / "compose_asset_board.py"
VALIDATOR = SCRIPT_DIR / "validate_asset_board_run.py"


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

    prompt = attempt / "final_generation_prompt.md"
    prompt.write_text(
        "Create one clean eight-view packaging board with exactly four fully populated detail panels. "
        "No blank cells, empty rectangles, placeholders, reserved slots, or unused panels.\n",
        encoding="utf-8",
        newline="\n",
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
            "background_rgb": [248, 248, 248],
        }
    )
    detail_aliases = ["front", "back", "three_quarter", "front"]
    for index, alias in enumerate(detail_aliases):
        overlays.append(
            {
                "region_id": f"detail_{index + 1}",
                "role": "detail",
                "source_path": str(frozen_paths[alias]),
                "source_sha256": sha(frozen_paths[alias]),
                "crop_box": [100, 300, 700, 900],
                "target_box": [index * 960, 1680, (index + 1) * 960, 2160],
                "fit": "contain",
                "background_rgb": [248, 248, 248],
            }
        )
    final_board = attempt / "final-board.png"
    write_json(
        plan,
        {
            "schema_version": "packaging_board_composition_plan.v1",
            "raw_board_path": str(raw),
            "raw_board_sha256": sha(raw),
            "output_board_path": str(final_board),
            "canvas_size": [3840, 2160],
            "base_fit": "cover",
            "detail_layout": [
                {"region_id": f"detail_{index + 1}", "target_box": [index * 960, 1680, (index + 1) * 960, 2160]}
                for index in range(4)
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
        {"view_id": "left_side", "evidence_status": "bounded_inferred"},
        {"view_id": "right_side", "evidence_status": "bounded_inferred"},
        {"view_id": "front_three_quarter", "evidence_status": "source_observed"},
        {"view_id": "rear_three_quarter", "evidence_status": "bounded_inferred"},
        {"view_id": "high_angle", "evidence_status": "bounded_inferred"},
        {"view_id": "low_angle", "evidence_status": "bounded_inferred"},
    ]
    details = [
        {
            "region_id": f"detail_{index + 1}",
            "evidence_status": "deterministic_reprojection",
            "source_alias": alias,
        }
        for index, alias in enumerate(detail_aliases)
    ]
    manifest = run_dir / "asset-board-manifest.json"
    manifest_value = {
        "schema_version": "packaging_video_asset_board.v1",
        "run_status": "COMPLETE",
        "input_profile": "one_to_three_reference",
        "reference_manifest_path": str(reference_manifest),
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
        "view_cells": views,
        "detail_cells": details,
        "qa": {
            "inspected": True,
            "eight_complete_views": "pass",
            "four_to_six_details": "pass",
            "identity_consistency": "pass",
            "label_fidelity": "pass",
            "source_anchor_match": "pass",
            "non_product_text_pollution": "pass",
            "all_cells_populated": "pass",
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
    }


class ContractTests(unittest.TestCase):
    def test_skill_declares_one_board_and_nonblocking_ocr(self) -> None:
        skill = (PACKAGE_DIR / "SKILL.md").read_text(encoding="utf-8")
        for token in [
            "exactly one clean horizontal 16:9 board",
            "exactly eight complete product views",
            "four to six fully populated evidence detail panels",
            "OCR remains nonblocking",
            "Do not make OCR completion a global gate",
            "never request a fixed 8/12/16/24-angle capture set",
            "The main agent must not call imagegen directly",
            "at most two repair attempts",
            "No blank cells, empty rectangles, placeholders, reserved slots",
            "independently usable as a final single-call prompt",
        ]:
            self.assertIn(token, skill)

    def test_prompt_template_is_standalone_and_population_safe(self) -> None:
        prompt = (PACKAGE_DIR / "references" / "generation_prompt_template.md").read_text(encoding="utf-8")
        for required in [
            "exactly {{detail_count}} fully populated",
            "{{detail_panel_list}}",
            "No blank cells, empty rectangles, placeholders, reserved slots",
            "independently usable",
            "Keep every bottle upright on its base",
        ]:
            self.assertIn(required, prompt)
        for forbidden in [
            "will be replaced",
            "Keep those six windows visually empty",
            "Do not place any generated close-up content",
        ]:
            self.assertNotIn(forbidden, prompt)

    def test_three_references_validate_with_unresolved_microcopy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = valid_fixture(Path(tmp))
            result = run([sys.executable, "-X", "utf8", str(VALIDATOR), "--manifest", str(fixture["manifest"])])
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["reference_count"], 3)
            self.assertEqual(payload["view_count"], 8)
            self.assertEqual(payload["detail_count"], 4)
            self.assertEqual(payload["copy_authority"], "video_reference")

    def test_missing_view_fails_without_requesting_more_sources(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = valid_fixture(Path(tmp))
            value = copy.deepcopy(fixture["value"])
            value["view_cells"].pop()
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
            value["detail_cells"][0]["region_id"] = "unbound_detail"
            write_json(fixture["manifest"], value)
            result = run([sys.executable, "-X", "utf8", str(VALIDATOR), "--manifest", str(fixture["manifest"])])
            self.assertEqual(result.returncode, 2)
            self.assertEqual(error_code(result), "blocked_composition_detail_mapping")


if __name__ == "__main__":
    unittest.main(verbosity=2)
