"""Expiry is a deadline; capture and verification timestamps are past events."""

from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import test_contract
from _contract_utils import parse_timestamp
from _evidence_binding import intent_constraints_sha256
from validate_research_run import PackValidator, validate_run


class FreshnessDeadlineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "run"
        test_contract.make_valid_run(self.root)
        self.now = datetime(2026, 7, 13, 1, 0, tzinfo=timezone.utc)

    def validator(self) -> PackValidator:
        contract = {"pack_id": "image_pack", "modality": "image", "qualified_target": 30, "selected_target": 20}
        validator = PackValidator(self.root, self.root, contract, SCRIPTS.parent / "references", self.now)
        self.assertTrue(validator._load())
        return validator

    def receipt_check(self, window: int = 120, *, expiry_delta: int = 0, age: int = 5) -> PackValidator:
        validator = self.validator()
        validator.artifacts["intent"]["freshness_need"]["final_receipt_window_minutes"] = window
        candidate = copy.deepcopy(validator.artifacts["candidates"][0])
        candidate["intent_alignment"]["intent_constraints_sha256"] = intent_constraints_sha256(validator.artifacts["intent"])
        receipt = copy.deepcopy(validator.artifacts["receipts"][0])
        checked = parse_timestamp(receipt["checked_at"])
        receipt["freshness"].update({"window_minutes": window, "expires_at": test_contract._iso(checked + timedelta(minutes=window + expiry_delta))})
        reference = checked + timedelta(minutes=age)
        validator.validation_now = reference
        validator._validate_candidate_and_receipt(candidate, receipt, candidate["status"], reference, window)
        return validator

    def test_full_contract_accepts_unexpired_future_deadlines(self) -> None:
        # The report is at 01:00, checks at 00:55, and expiry at 01:25.
        # All occurrence timestamps are valid at the real delivery clock.
        result = validate_run(self.root, validation_now=self.now)
        self.assertEqual(result["status"], "PASS", result["findings"])
        self.assertFalse(result["production_deliverable"])

    def test_120_minute_receipt_keeps_its_actual_future_deadline(self) -> None:
        validator = self.receipt_check()
        self.assertEqual(validator.findings, [])

    def test_wrong_deadline_still_fails_frozen_window(self) -> None:
        validator = self.receipt_check(expiry_delta=1)
        self.assertTrue(any(f.code == "FRESHNESS-01" and "expiry must equal" in f.message for f in validator.findings))

    def test_expired_receipt_still_fails_delivery_freshness(self) -> None:
        validator = self.receipt_check(age=121)
        self.assertTrue(any(f.code == "FRESHNESS-01" and "outside delivery freshness window" in f.message for f in validator.findings))

    def test_future_occurrences_remain_rejected(self) -> None:
        for label in ("checked_at", "generated_at", "capture.captured_at", "discovered_at"):
            with self.subTest(label=label):
                validator = self.validator()
                validator._time(test_contract._iso(self.now + timedelta(minutes=6)), label)
                self.assertTrue(any("trusted validation clock" in f.message for f in validator.findings))

    def test_deadline_without_timezone_is_rejected(self) -> None:
        validator = self.validator()
        self.assertIsNone(validator._time("2026-07-13T01:25:00", "expires_at", is_deadline=True))
        self.assertTrue(validator.findings)


if __name__ == "__main__":
    unittest.main()
