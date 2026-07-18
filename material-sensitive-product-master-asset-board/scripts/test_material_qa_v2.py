#!/usr/bin/env python3
"""Research-aware QA v4 contract tests."""

from __future__ import annotations

import copy
import unittest
from pathlib import Path

from material_contract import MaterialContractError, normalize_source_contract_draft
from material_decision_records import (
    board_gate_keys,
    build_qa_record,
    fact_sources,
    normalize_decision,
    panel_result_keys,
)
from test_material_coverage_contract import clear_front_draft, manifest


def build_contract() -> dict[str, object]:
    return normalize_source_contract_draft(clear_front_draft(), manifest("product_front"))


def build_decision(contract: dict[str, object]) -> dict[str, object]:
    sources_by_fact = fact_sources(contract)
    gates = {key: "pass" for key in board_gate_keys(contract)}
    gates["state_window_source_supported"] = "not_used"
    return {
        "schema_version": "material_board_qa_decision.v2",
        "attempt_id": "01",
        "comparison_mode": "source_to_board_visual_comparison",
        "assistant_qa_status": "passed",
        "production_approval_status": "not_granted",
        "board_gates": gates,
        "panel_results": [
            {
                "panel_id": panel["panel_id"],
                "source_aliases": panel["source_aliases"],
                "invariant_ids": panel["invariant_ids"],
                "status": "pass",
                "source_fidelity": "pass",
                "source_observation": f"Frozen evidence for {panel['panel_id']} was inspected.",
                "board_observation": f"Rendered panel {panel['panel_id']} preserves that evidence.",
                "view_authority": panel["view_authority"],
                "target_surfaces": panel["target_surfaces"],
                "research_claim_ids": panel["research_claim_ids"],
                "research_grade_status": "pass",
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
                "source_observation": f"Frozen sources establish {invariant['invariant_id']}.",
                "board_observation": f"The board preserves {invariant['invariant_id']}.",
            }
            for invariant in contract["critical_invariants"]
        ],
        "observed_defects": [],
        "repair_required": False,
        "repair_reasons": [],
    }


class ResearchAwareQaTests(unittest.TestCase):
    def test_research_aware_panel_keys_include_authority_bindings(self) -> None:
        self.assertEqual(
            panel_result_keys({"schema_version": "material_source_contract.v2"})
            - panel_result_keys({"schema_version": "material_source_contract.v1"}),
            {
                "view_authority",
                "target_surfaces",
                "research_claim_ids",
                "research_grade_status",
            },
        )

    def test_v2_decision_binds_panel_research_authority_and_builds_qa_v4(self) -> None:
        contract = build_contract()
        decision = build_decision(contract)
        normalized = normalize_decision(
            decision, contract=contract, manifest={"aliases": ["product_front"]}
        )
        self.assertEqual("pass", normalized["board_gates"]["research_grade_compliant"])
        qa = build_qa_record(
            decision=decision,
            decision_path=Path("qa_decision.json"),
            decision_sha256="a" * 64,
            board_path=Path("board.png"),
            board_sha256="b" * 64,
            width_px=1672,
            height_px=941,
            worker_thread_id="worker-thread",
            image_generation_call_id="image-call",
            contract=contract,
            manifest={"aliases": ["product_front"], "entries": []},
        )
        self.assertEqual("material_board_qa.v4", qa["schema_version"])

    def test_v2_rejects_panel_authority_laundering_in_qa(self) -> None:
        contract = build_contract()
        decision = build_decision(contract)
        decision["panel_results"][0]["target_surfaces"] = ["rear"]
        with self.assertRaises(MaterialContractError) as caught:
            normalize_decision(
                decision, contract=contract, manifest={"aliases": ["product_front"]}
            )
        self.assertEqual("blocked_board_inspection_invalid", caught.exception.code)

    def test_v2_research_grade_failure_cannot_claim_passed_qa(self) -> None:
        contract = build_contract()
        decision = build_decision(contract)
        decision["panel_results"][0]["research_grade_status"] = "fail"
        with self.assertRaises(MaterialContractError) as caught:
            normalize_decision(
                decision, contract=contract, manifest={"aliases": ["product_front"]}
            )
        self.assertEqual("blocked_board_inspection_invalid", caught.exception.code)

    def test_v2_requires_all_research_gates(self) -> None:
        contract = build_contract()
        decision = build_decision(contract)
        del decision["board_gates"]["hidden_copy_non_fabricated"]
        with self.assertRaises(MaterialContractError) as caught:
            normalize_decision(
                decision, contract=contract, manifest={"aliases": ["product_front"]}
            )
        self.assertEqual("blocked_board_inspection_invalid", caught.exception.code)


if __name__ == "__main__":
    unittest.main(verbosity=2)
