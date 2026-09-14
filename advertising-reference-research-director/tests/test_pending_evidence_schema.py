#!/usr/bin/env python3
"""Pending evidence is serializable; it can never masquerade as final evidence."""

from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT / "scripts"))

from _contract_utils import read_json, read_jsonl, write_json, write_jsonl
from _json_schema_subset import assert_schema_supported, validate
from test_contract import _candidate, _capture_record, _make_intent, _receipt, _refresh_report_contracts, make_valid_run
from validate_research_run import PackValidator, validate_run
from verify_candidates import _blocked_receipt


def pending_candidate(candidate: dict, status: str = "raw") -> dict:
    """Keep discovery identity; explicitly withhold every unobserved assessment."""
    result = copy.deepcopy(candidate)
    result.update(status=status, verification_receipt_id=None)
    result["access_state"] = {
        "mode": "unknown", "state": "unknown", "checked_url": None,
        "page_rendered": None, "canonical_url_resolved": None,
        "shareable_without_session": "unknown", "http_status": None,
        "challenge_detected": None,
    }
    result["provenance_check"] = {
        "status": "pending", "accountable_url": None, "accountable_owner": None,
        "source_signal": "discovery_only", "matched_object": None,
    }
    result["source"]["evidence_tier"] = "discovery_only"
    result["object"]["asset_locator"] = None
    result["object"]["stable_id"] = None
    for field in ("intent_alignment", "evaluation_dimensions", "diversity"):
        result[field] = None
    for right in result["rights_scope"].values():
        right.update(state="unknown", basis="No access or permission assessment has been performed.")
    result["dedup"].update(fingerprint=None, stable_id_key=None, version_relation="unknown")
    result["agent_trace"]["finder_decision"] = "proposed" if status == "raw" else "screened_in"
    return result


class PendingEvidenceSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.candidate_schema = read_json(PACKAGE_ROOT / "references/candidate_item.schema.json")
        cls.capture_schema = read_json(PACKAGE_ROOT / "references/browser_capture_record.schema.json")
        cls.receipt_schema = read_json(PACKAGE_ROOT / "references/verification_receipt.schema.json")
        assert_schema_supported(cls.candidate_schema)
        assert_schema_supported(cls.capture_schema)
        assert_schema_supported(cls.receipt_schema)

    def test_raw_and_screened_can_be_saved_without_invented_observations(self):
        for modality in ("image", "video"):
            for status in ("raw", "screened"):
                with self.subTest(modality=modality, status=status):
                    candidate = pending_candidate(_candidate("pending_fixture", modality, 0), status)
                    self.assertEqual([], validate(json.loads(json.dumps(candidate)), self.candidate_schema))

    def test_every_new_pending_value_is_independently_rejected_in_all_final_states(self):
        mutations = [
            ("access_state", "mode", "unknown"),
            ("access_state", "state", "unknown"),
            ("access_state", "checked_url", None),
            ("access_state", "page_rendered", None),
            ("access_state", "canonical_url_resolved", None),
            ("access_state", "challenge_detected", None),
            ("provenance_check", "status", "pending"),
            ("provenance_check", "matched_object", None),
            (None, "intent_alignment", None),
            (None, "evaluation_dimensions", None),
            (None, "diversity", None),
            (None, "verification_receipt_id", None),
            ("object", "asset_locator", None),
        ]
        for modality in ("image", "video"):
            for status in ("qualified", "selected", "rejected"):
                baseline = _candidate("pending_fixture", modality, 0)
                baseline["status"] = status
                self.assertEqual([], validate(baseline, self.candidate_schema))
                for section, field, value in mutations:
                    with self.subTest(modality=modality, status=status, field=f"{section}.{field}"):
                        candidate = copy.deepcopy(baseline)
                        target = candidate if section is None else candidate[section]
                        target[field] = value
                        self.assertTrue(validate(candidate, self.candidate_schema))

    def test_existing_session_bound_unknown_shareability_is_not_reclassified(self):
        candidate = _candidate("pending_fixture", "video", 0)
        candidate["access_state"].update(mode="signed_chrome", state="session_bound", shareable_without_session="unknown")
        self.assertEqual([], validate(candidate, self.candidate_schema))

    def test_nonfinal_record_can_preserve_an_existing_failed_receipt_reference(self):
        candidate = pending_candidate(_candidate("pending_fixture", "video", 0), "screened")
        candidate["verification_receipt_id"] = "receipt_previous_failed_attempt"
        self.assertEqual([], validate(candidate, self.candidate_schema))

    def test_failed_capture_can_report_no_media_locator_but_cannot_claim_media_success(self):
        for modality in ("image", "video"):
            candidate = _candidate("pending_fixture", modality, 0)
            receipt = _receipt(candidate, datetime(2026, 9, 14, tzinfo=timezone.utc), "unassigned_pack")
            baseline = _capture_record(candidate, receipt, "unassigned_pack", "0" * 64)
            self.assertEqual([], validate(baseline, self.capture_schema))
            failed = copy.deepcopy(baseline)
            observation = failed["observation"]
            observation.update(asset_locator=None, stable_id=None, dedup_fingerprint=None)
            observation["media_check"]["status"] = "failed"
            if modality == "video":
                observation["media_check"]["video_playback"].update(
                    player_present=False, playback_started=False, observed_progress_seconds=0,
                    duration_seconds=None, specific_work_matched=False,
                )
            else:
                observation["media_check"]["image_render"].update(
                    rendered=False, asset_locator=None, natural_width=None,
                    natural_height=None, placeholder_detected=False,
                )
            self.assertEqual([], validate(failed, self.capture_schema))
            for change in ("passed", "missing_status", "fingerprint", "empty_locator"):
                with self.subTest(modality=modality, change=change):
                    invalid = copy.deepcopy(failed)
                    observed = invalid["observation"]
                    if change == "passed":
                        observed["media_check"]["status"] = "passed"
                    elif change == "missing_status":
                        observed["media_check"] = {}
                    elif change == "fingerprint":
                        observed["dedup_fingerprint"] = baseline["observation"]["dedup_fingerprint"]
                    else:
                        observed["asset_locator"] = ""
                    self.assertTrue(validate(invalid, self.capture_schema))

    def test_full_run_accepts_additional_pending_raw_without_counting_it_as_final(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            make_valid_run(root)
            self.assertEqual("PASS", validate_run(root)["status"])
            ledger_path = root / "02_candidates/candidate_ledger.jsonl"
            rows = read_jsonl(ledger_path)
            raw = pending_candidate(rows[0])
            raw["candidate_id"] = "candidate_pending_unobserved"
            rows.append(raw)
            write_jsonl(ledger_path, rows)
            registry_path = root / "01_orchestration/approach_registry.json"
            registry = read_json(registry_path)
            approach = next(item for item in registry["approaches"] if item["approach_id"] == raw["agent_trace"]["approach_id"])
            approach["returned_count"] += 1
            approach["qualification_rate"] = round(approach["qualified_count"] / approach["returned_count"], 3)
            approach["failure_records"][0]["candidate_ids"].append(raw["candidate_id"])
            write_json(registry_path, registry)
            _refresh_report_contracts(root, root)
            result = validate_run(root)
            self.assertEqual("PASS", result["status"], json.dumps(result, ensure_ascii=False, indent=2))
            # Promotion is invalid without fresh evidence even when identity is unchanged.
            rows[-1]["status"] = "qualified"
            write_jsonl(ledger_path, rows)
            self.assertNotEqual("PASS", validate_run(root)["status"])

    def test_blocked_image_receipt_does_not_invent_locator_dimensions_or_placeholder(self):
        baseline = _candidate("pending_fixture", "image", 0)
        access = copy.deepcopy(baseline["access_state"])
        access.update(state="blocked", page_rendered=False)
        for locator in (None, "", "   ", "observed-image-locator"):
            with self.subTest(locator=locator):
                candidate = copy.deepcopy(baseline)
                candidate["object"]["asset_locator"] = locator
                receipt = _blocked_receipt(candidate, "independent_verifier", access=access,
                                           evidence_locator=candidate["object"]["canonical_url"])
                image = receipt["media_check"]["image_render"]
                self.assertEqual(locator if locator and locator.strip() else None, image["asset_locator"])
                for field in ("natural_width", "natural_height", "placeholder_detected"):
                    self.assertIsNone(image[field])
                self.assertEqual([], validate(receipt, self.receipt_schema))
                receipt["outcome"] = "failed"
                self.assertEqual([], validate(receipt, self.receipt_schema))
                for field, value in (("rendered", True), ("asset_locator", "")):
                    invalid = copy.deepcopy(receipt)
                    invalid["media_check"]["image_render"][field] = value
                    self.assertTrue(validate(invalid, self.receipt_schema))
                invalid = copy.deepcopy(receipt)
                invalid["media_check"]["status"] = "passed"
                self.assertTrue(validate(invalid, self.receipt_schema))

    def test_qualified_image_receipt_rejects_every_unknown_image_field(self):
        candidate = _candidate("pending_fixture", "image", 0)
        receipt = _receipt(candidate, datetime(2026, 9, 14, tzinfo=timezone.utc), "unassigned_pack")
        receipt["capture_bindings"] = [{"capture_id": "capture_test", "record_sha256": "0" * 64,
                                        "purposes": ["media"]}]
        self.assertEqual([], validate(receipt, self.receipt_schema))
        for field in ("asset_locator", "natural_width", "natural_height", "placeholder_detected"):
            with self.subTest(field=field):
                invalid = copy.deepcopy(receipt)
                invalid["media_check"]["image_render"][field] = None
                self.assertTrue(validate(invalid, self.receipt_schema))

    def test_temporal_only_contribution_requires_portfolio_policy_and_at_least_one_axis(self):
        contract = {"pack_id": "video_pack", "modality": "video", "qualified_target": 30, "selected_target": 20}
        intent = _make_intent("axis_fixture", "video", [contract], "single_modality")
        now = datetime(2026, 7, 13, tzinfo=timezone.utc)

        def check(policy_enabled: bool, temporal_axes: list[str]):
            current_intent = copy.deepcopy(intent)
            if policy_enabled:
                current_intent["coverage_policy"] = {
                    "mode": "portfolio_complementary_v1", "hard_visual_axes": [],
                    "hard_temporal_axes": [], "minimum_matched_axes": 1,
                    "selected_min_support_per_axis": 1,
                }
            candidate = _candidate("axis_fixture", "video", 0, "video_pack", current_intent)
            candidate["intent_alignment"].update(visual_axes_matched=[], temporal_axes_matched=temporal_axes)
            self.assertEqual([], validate(candidate, self.candidate_schema))
            validator = PackValidator(PACKAGE_ROOT, PACKAGE_ROOT, contract, PACKAGE_ROOT / "references", now)
            validator.artifacts["intent"] = current_intent
            validator._validate_intent_alignment(candidate, now)
            return validator.findings

        self.assertTrue(intent["temporal_axes"])
        self.assertEqual([], check(True, intent["temporal_axes"][:1]))
        self.assertTrue(any(f.code == "RELEVANCE-01" for f in check(True, [])))
        self.assertTrue(any(f.code == "RELEVANCE-01" for f in check(False, intent["temporal_axes"])))


if __name__ == "__main__":
    unittest.main()
