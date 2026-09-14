#!/usr/bin/env python3
"""Quantity checkpoints suggest work; they never attest media or completion."""
from __future__ import annotations

import copy
import hashlib
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT / "scripts"))

from _contract_utils import read_json, read_jsonl, write_json, write_jsonl
from research_progress import checkpoint
from test_contract import _candidate, _capture_record, _receipt, make_parallel_run, make_valid_run
from validate_research_run import PACK_PATHS


class ResearchProgressTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        make_valid_run(self.root, "video")

    def load_rows(self, name):
        return read_jsonl(self.root / PACK_PATHS[name])

    def save_rows(self, name, rows):
        write_jsonl(self.root / PACK_PATHS[name], rows)

    def counts(self, *, total, ready, selected=0, pending=False):
        """Synthetic observed-media fixtures, deliberately not a final contract."""
        intent = read_json(self.root / "00_intent/intent_brief.json")
        candidates, receipts, captures = [], [], []
        now = datetime(2026, 7, 13, tzinfo=timezone.utc)
        for index in range(total):
            candidate = _candidate("fixture_run", "video", index, "video_pack", intent)
            if index < ready:
                candidate["status"] = "screened"
                receipt = _receipt(candidate, now, "video_pack")
                receipt.update(outcome="failed", evidence_level="E3_MEDIA_CONFIRMED", failure_codes=["OTHER"])
                capture = _capture_record(candidate, receipt, "video_pack", "0" * 64)
                receipts.append(receipt)
                captures.append(capture)
            else:
                candidate.update(status="raw" if pending else "quarantined", verification_receipt_id=None)
            candidates.append(candidate)
        self.save_rows("candidates", candidates)
        self.save_rows("receipts", receipts)
        self.save_rows("captures", captures)
        for key, ids in (("shortlist", []), ("selected", candidates[:selected]), ("rejected", [])):
            write_json(self.root / PACK_PATHS[key], {"items": [{"candidate_id": c["candidate_id"]} for c in ids]})

    def check(self):
        result = checkpoint(self.root)
        self.assertFalse(result["production_deliverable"])
        self.assertNotIn(result["status"], {"completed", "production_ready"})
        return result, result["packs"][0]

    def test_exhausted_59_or_100_candidates_with_17_selected_requires_new_wave(self):
        for total in (59, 100):
            with self.subTest(total=total):
                self.counts(total=total, ready=17, selected=17)
                result, pack = self.check()
                self.assertEqual("continue_work", result["status"])
                self.assertEqual("register_new_search_wave", pack["next_action"])
                self.assertEqual(total, pack["raw_distinct_candidates"])
                self.assertEqual(3, pack["selected_gap"])

    def test_pending_backlog_requires_verification_and_expansion(self):
        self.counts(total=59, ready=17, selected=17, pending=True)
        _, pack = self.check()
        self.assertEqual("verify_backlog_and_expand_search", pack["next_action"])
        self.assertEqual(42, pack["pending_media_candidates"])

    def test_30_provisional_media_trigger_curation_without_promoting_unsigned_e3(self):
        self.counts(total=30, ready=30)
        before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in self.root.rglob("*") if p.is_file()}
        result, pack = self.check()
        self.assertEqual("curate_and_verify_full_pool", pack["next_action"])
        self.assertEqual(30, pack["media_ready_provisional"])
        self.assertIsNone(result["validation"])
        self.assertTrue(all(r["evidence_level"] == "E3_MEDIA_CONFIRMED" for r in self.load_rows("receipts")))
        after = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in self.root.rglob("*") if p.is_file()}
        self.assertEqual(before, after)

    def test_20_selected_without_30_and_10_continues_search(self):
        self.counts(total=20, ready=20, selected=20)
        _, pack = self.check()
        self.assertEqual(0, pack["selected_gap"])
        self.assertEqual(10, pack["provisional_pool_gap"])
        self.assertEqual("register_new_search_wave", pack["next_action"])

    def test_fixture_gets_fresh_validation_and_ignores_forged_cached_pass(self):
        write_json(self.root / "06_output/validation_result.json", {
            "status": "PASS", "production_contract_eligible": True, "production_ready": True,
            "checked_at": "2000-01-01T00:00:00Z", "cache_marker": "must-not-be-trusted",
        })
        result, pack = self.check()
        self.assertEqual("validate_full_package", pack["next_action"])
        self.assertIsInstance(result["validation"], dict)
        self.assertNotEqual("must-not-be-trusted", result["validation"].get("cache_marker"))
        self.assertEqual("continue_work", result["status"])
        self.assertIsNot(result["validation"].get("production_contract_eligible"), True)

    def test_current_pointer_excludes_old_success_and_invalidated_or_quarantined_rows(self):
        self.counts(total=4, ready=4)
        candidates, receipts = self.load_rows("candidates"), self.load_rows("receipts")
        failed = copy.deepcopy(receipts[0])
        failed["receipt_id"] = "receipt_current_failure"
        failed["media_check"]["status"] = "failed"
        candidates[0]["verification_receipt_id"] = failed["receipt_id"]
        candidates[1]["status"] = "invalidated"
        candidates[2]["status"] = "quarantined"
        receipts.append(failed)
        self.save_rows("candidates", candidates)
        self.save_rows("receipts", receipts)
        _, pack = self.check()
        self.assertEqual(1, pack["media_ready_provisional"])
        self.assertEqual(1, pack["pending_media_candidates"])

    def test_either_stable_id_or_url_and_transitive_aliases_suppress_duplicates(self):
        self.counts(total=5, ready=5)
        candidates = self.load_rows("candidates")
        candidates[1]["object"]["stable_id"] = candidates[0]["object"]["stable_id"]
        candidates[3]["object"]["canonical_url"] = candidates[2]["object"]["canonical_url"] + "#player"
        # Last row bridges the two prior groups. It must not preserve two counts.
        candidates[4]["object"]["stable_id"] = candidates[0]["object"]["stable_id"]
        candidates[4]["object"]["canonical_url"] = candidates[2]["object"]["canonical_url"]
        self.save_rows("candidates", candidates)
        _, pack = self.check()
        self.assertEqual(1, pack["media_ready_provisional"])

    def test_foreign_pack_candidates_receipts_and_captures_do_not_count(self):
        self.counts(total=4, ready=4, selected=4)
        candidates, receipts, captures = (self.load_rows(n) for n in ("candidates", "receipts", "captures"))
        candidates[0]["pack_id"] = "foreign_pack"
        receipts[1]["pack_id"] = "foreign_pack"
        captures[2]["pack_id"] = "foreign_pack"
        for name, rows in (("candidates", candidates), ("receipts", receipts), ("captures", captures)):
            self.save_rows(name, rows)
        _, pack = self.check()
        self.assertEqual(3, pack["raw_distinct_candidates"])
        self.assertEqual(3, pack["selected_declared"])
        self.assertEqual(1, pack["media_ready_provisional"])
        self.assertEqual(2, pack["pending_media_candidates"])

    def test_parallel_pack_counts_remain_separate(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            make_parallel_run(root)
            video_root = root / "packs/video_pack"
            candidates = read_jsonl(video_root / PACK_PATHS["candidates"])
            for row in candidates:
                row["status"] = "invalidated"
            write_jsonl(video_root / PACK_PATHS["candidates"], candidates)
            write_json(video_root / PACK_PATHS["shortlist"], {"items": []})
            result = checkpoint(root)
            packs = {p["pack_id"]: p for p in result["packs"]}
            self.assertEqual(30, packs["image_pack"]["media_ready_provisional"])
            self.assertEqual(0, packs["video_pack"]["media_ready_provisional"])
            self.assertEqual("register_new_search_wave", packs["video_pack"]["next_action"])
            self.assertFalse(result["production_deliverable"])


if __name__ == "__main__":
    unittest.main()
