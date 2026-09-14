#!/usr/bin/env python3
"""Full-run regressions for complementary references and honest curation.

All observations are explicit synthetic fixtures, never live-media verification.
Fixture mutations refresh capture, receipt, intent, dedup, review, gallery and
report bindings so a hash error cannot accidentally satisfy a semantic test.
Run: python -B tests/test_selection_recovery.py
"""

from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT / "scripts"))

from _contract_utils import read_json, read_jsonl, write_json, write_jsonl
from _evidence_binding import dedup_comparison_set_sha256
from test_contract import (
    _refresh_approach_plan_bindings,
    _refresh_candidate_intent_bindings,
    _refresh_report_contracts,
    build_gallery,
    make_valid_run,
)
from validate_research_run import normalize_url, validate_run


INTENT = "00_intent/intent_brief.json"
REGISTRY = "01_orchestration/approach_registry.json"
LEDGER = "02_candidates/candidate_ledger.jsonl"
RECEIPTS = "03_verification/verification_receipts.jsonl"
CAPTURES = "03_verification/browser_capture_records.jsonl"
SHORTLIST = "04_selection/shortlist_30.json"
SELECTED = "04_selection/selected_20.json"
REJECTED = "04_selection/rejected_10.json"
REPORT = "06_output/verification_report.json"
REVIEW = "04_selection/review/diversity.json"


def change_json(root: Path, relative: str, edit) -> None:
    document = read_json(root / relative)
    edit(document)
    write_json(root / relative, document)


def change_intent(root: Path, edit) -> None:
    # The bundled fixture replays a v1 -> v2 scene-scale correction. Add the
    # new, initially frozen policy to both snapshots, not as an undeclared edit.
    change_json(root, INTENT, edit)
    change_json(root, "00_intent/intent_brief.v1.snapshot.json", edit)


def change_candidates(root: Path, edit) -> None:
    rows = read_jsonl(root / LEDGER)
    edit(rows)
    write_jsonl(root / LEDGER, rows)


def seal(root: Path) -> dict:
    """Rebind fixture artifacts; never bypass the production run validator."""
    _refresh_candidate_intent_bindings(root, root)
    shortlist = set(read_json(root / SHORTLIST)["candidate_ids"])
    candidates = [c for c in read_jsonl(root / LEDGER) if c["candidate_id"] in shortlist]
    digest = dedup_comparison_set_sha256(candidates)
    receipts = read_jsonl(root / RECEIPTS)
    for receipt in receipts:
        if receipt["candidate_id"] in shortlist:
            receipt["dedup_check"]["comparison_set_sha256"] = digest
    write_jsonl(root / RECEIPTS, receipts)
    _refresh_approach_plan_bindings(root)
    (root / "06_output/reference_board.html").write_text(build_gallery(root), encoding="utf-8")
    _refresh_report_contracts(root, root)
    return validate_run(root)


def complementary(root: Path) -> None:
    policy = {
        "mode": "portfolio_complementary_v1",
        "hard_visual_axes": [],
        "hard_temporal_axes": [],
        "minimum_matched_axes": 1,
        "selected_min_support_per_axis": 2,
    }
    change_intent(root, lambda intent: intent.update(coverage_policy=policy))
    intent = read_json(root / INTENT)
    rows = read_jsonl(root / LEDGER)
    for index, candidate in enumerate(rows):
        alignment = candidate["intent_alignment"]
        alignment["visual_axes_matched"] = [intent["visual_axes"][index % 2]]
        if candidate["modality"] == "video":
            alignment["temporal_axes_matched"] = [intent["temporal_axes"][index % 2]]
    write_jsonl(root / LEDGER, rows)


def antichain(root: Path) -> None:
    """Thirty genuinely incomparable vectors; no score changes after selection."""
    ids = read_json(root / SHORTLIST)["candidate_ids"]
    rows = read_jsonl(root / LEDGER)
    for row in rows:
        if row["candidate_id"] not in ids:
            continue
        index = ids.index(row["candidate_id"])
        for name, dimension in row["evaluation_dimensions"].items():
            dimension["score"] = 30 + index if name == "relevance" else 80 - index if name == "craft_signal" else 50
            dimension["rationale"] = f"Synthetic antichain: item {index} trades increasing relevance against decreasing craft."
    write_jsonl(root / LEDGER, rows)
    rejected = read_json(root / REJECTED)
    for item in rejected["items"]:
        item.update(
            comparison_kind="curatorial_tradeoff",
            dominance_dimension="craft_signal",
            dominance_reason="Prefer the comparator's craft for this execution study while conceding lower relevance.",
            score_tie_break=None,
            tradeoff={
                "selected_advantages": ["craft_signal"],
                "rejected_advantages": ["relevance"],
                "decision_rationale": "This synthetic execution study prioritizes resolved craft while explicitly accepting the comparator's lower relevance.",
            },
        )
    write_json(root / REJECTED, rejected)


def sync_provenance_observations(root: Path) -> None:
    """Apply a deliberate synthetic observation change to its real bindings."""
    candidates = {c["candidate_id"]: c for c in read_jsonl(root / LEDGER)}
    receipts = read_jsonl(root / RECEIPTS)
    for receipt in receipts:
        candidate = candidates[receipt["candidate_id"]]
        receipt["source_id"] = candidate["source"]["source_id"]
        receipt["access_state"] = copy.deepcopy(candidate["access_state"])
        receipt["provenance_check"] = copy.deepcopy(candidate["provenance_check"])
        for evidence in receipt["evidence"]:
            if evidence["kind"] == "url":
                evidence["locator"] = candidate["object"]["canonical_url"]
    write_jsonl(root / RECEIPTS, receipts)
    captures = read_jsonl(root / CAPTURES)
    for capture in captures:
        candidate = candidates[capture["candidate_id"]]
        observation = capture["observation"]
        observation["canonical_url"] = candidate["object"]["canonical_url"]
        observation["access_state"] = copy.deepcopy(candidate["access_state"])
        observation["provenance_check"] = copy.deepcopy(candidate["provenance_check"])
    write_jsonl(root / CAPTURES, captures)


def creative_metrics(root: Path) -> None:
    """Independently count fixture owners instead of copying validator output."""
    ids = {c["candidate_id"] for c in read_json(root / SELECTED)["items"]}
    owners = [" ".join(c["provenance_check"]["accountable_owner"].casefold().split())
              for c in read_jsonl(root / LEDGER) if c["candidate_id"] in ids]
    metrics = {
        "distinct_domains": 1, "distinct_source_families": 1,
        "territory_count": 5, "max_per_domain": 20,
        "max_per_campaign_or_creator": 1, "max_per_near_duplicate_group": 1,
        "distinct_accountable_origins": len(set(owners)),
        "max_per_accountable_origin": max(Counter(owners).values()),
    }
    change_json(root, SELECTED, lambda d: d["diversity_policy"].update(metrics, profile="creative_origin_v1"))
    change_json(root, REPORT, lambda d: d["diversity"].update(metrics, profile="creative_origin_v1"))
    change_json(root, REVIEW, lambda d: d.update(metrics=metrics))


def one_host_many_owners(root: Path) -> None:
    change_intent(root, lambda d: d["diversity_requirements"].update(
        profile="creative_origin_v1", min_accountable_origins=10, max_per_accountable_origin=2))
    rows = read_jsonl(root / LEDGER)
    for row in rows:
        url = "https://youtube.com/watch?v=" + row["object"]["stable_id"]
        row["object"]["canonical_url"] = url
        row["source"].update(source_id="runtime:youtube.com", source_family_id="first_party",
                             domain="youtube.com", discovered_url=url)
        row["access_state"]["checked_url"] = url
        row["provenance_check"]["accountable_url"] = url
        row["dedup"]["canonical_url_key"] = normalize_url(url)
        row["dedup"]["stable_id_key"] = "runtime:youtube.com:" + row["object"]["stable_id"]
    write_jsonl(root / LEDGER, rows)
    registry = read_json(root / REGISTRY)
    for approach in registry["approaches"]:
        approach["source_family_ids"] = ["first_party"]
        for failure in approach["failure_records"]:
            failure["source_family_id"] = "first_party"
    write_json(root / REGISTRY, registry)
    sync_provenance_observations(root)
    creative_metrics(root)


class SelectionRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="selection-recovery-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "synthetic_run"
        make_valid_run(self.root, "video")

    def passed(self):
        result = seal(self.root)
        self.assertEqual([], result["findings"], json.dumps(result["findings"], indent=2))

    def failed(self, code: str, message: str):
        findings = seal(self.root)["findings"]
        # Fail only for the intended semantic gate; schema/hash errors must not
        # mask an invalid positive setup or become a false-positive regression.
        self.assertTrue(findings, "invalid fixture unexpectedly passed")
        self.assertTrue(any(f["code"] == code and message in f["message"] for f in findings), findings)
        self.assertEqual({code}, {f["code"] for f in findings}, findings)

    def test_legacy_complete_run_passes(self):
        self.passed()

    def test_complementary_visual_and_temporal_axes_pass_full_run(self):
        complementary(self.root)
        self.passed()

    def test_legacy_partial_axis_still_fails(self):
        change_candidates(self.root, lambda rows: rows[0]["intent_alignment"].update(visual_axes_matched=["monumental set"]))
        self.failed("RELEVANCE-01", "every frozen visual axis")

    def test_missing_explicit_hard_visual_axis_fails(self):
        complementary(self.root)
        change_intent(self.root, lambda d: d["coverage_policy"].update(hard_visual_axes=["controlled material palette"]))
        self.failed("RELEVANCE-01", "per-item hard axis")

    def test_missing_explicit_hard_temporal_axis_fails(self):
        complementary(self.root)
        change_intent(self.root, lambda d: d["coverage_policy"].update(hard_temporal_axes=["edit rhythm"]))
        self.failed("RELEVANCE-01", "per-item hard axis")

    def test_must_have_is_not_relaxed_by_portfolio_mode(self):
        complementary(self.root)
        change_candidates(self.root, lambda rows: rows[0]["intent_alignment"].update(must_have_evidence=[]))
        self.failed("RELEVANCE-01", "must-have evidence")

    def test_explicit_human_presence_remains_hard(self):
        complementary(self.root)
        change_candidates(self.root, lambda rows: rows[0]["intent_alignment"].update(observed_human_presence="none"))
        self.failed("RELEVANCE-01", "human presence contradicts")

    def test_explicit_exclusion_remains_hard(self):
        complementary(self.root)
        change_candidates(self.root, lambda rows: rows[0]["intent_alignment"].update(must_not_have_checks=[]))
        self.failed("RELEVANCE-01", "exclusions do not exactly cover")

    def test_axis_seen_only_in_rejected_items_does_not_cover_selected(self):
        complementary(self.root)
        ids = {c["candidate_id"] for c in read_json(self.root / SELECTED)["items"]}
        def edit(rows):
            for row in rows:
                if row["candidate_id"] in ids:
                    row["intent_alignment"]["visual_axes_matched"] = ["monumental set"]
        change_candidates(self.root, edit)
        self.failed("RELEVANCE-01", "selected portfolio leaves axis uncovered")

    def test_undeclared_axis_claim_fails(self):
        complementary(self.root)
        change_candidates(self.root, lambda rows: rows[0]["intent_alignment"]["visual_axes_matched"].append("invented axis"))
        self.failed("RELEVANCE-01", "undeclared or wrong-modality axes")

    def test_thirty_nondominated_candidates_can_be_curated_without_score_fabrication(self):
        antichain(self.root)
        self.passed()

    def test_hiding_a_tradeoff_concession_fails(self):
        antichain(self.root)
        change_json(self.root, REJECTED, lambda d: d["items"][0]["tradeoff"].update(rejected_advantages=["source_authority"]))
        self.failed("CURATION-02", "exact score advantages and concessions")

    def test_legacy_pareto_rejects_the_same_antichain(self):
        antichain(self.root)
        def edit(d):
            for item in d["items"]:
                item.pop("comparison_kind")
                item.pop("tradeoff")
        change_json(self.root, REJECTED, edit)
        self.failed("CURATION-02", "does not Pareto-dominate")

    def test_tradeoff_treats_higher_rights_risk_as_a_concession(self):
        antichain(self.root)
        rejected = read_json(self.root / REJECTED)
        item = rejected["items"][0]
        comparator_id = item["dominated_by_candidate_ids"][0]
        def edit(rows):
            for row in rows:
                if row["candidate_id"] == comparator_id:
                    row["evaluation_dimensions"]["rights_risk"].update(
                        score=80, rationale="Synthetic comparator carries greater declared rights uncertainty.")
        change_candidates(self.root, edit)
        item["tradeoff"]["rejected_advantages"].append("rights_risk")
        write_json(self.root / REJECTED, rejected)
        self.passed()

    def test_tradeoff_cannot_hide_higher_rights_risk(self):
        antichain(self.root)
        item = read_json(self.root / REJECTED)["items"][0]
        comparator_id = item["dominated_by_candidate_ids"][0]
        def edit(rows):
            for row in rows:
                if row["candidate_id"] == comparator_id:
                    row["evaluation_dimensions"]["rights_risk"].update(
                        score=80, rationale="Synthetic comparator carries greater declared rights uncertainty.")
        change_candidates(self.root, edit)
        self.failed("CURATION-02", "exact score advantages and concessions")

    def test_twenty_verified_fixture_owners_on_youtube_pass_creative_profile(self):
        one_host_many_owners(self.root)
        self.passed()

    def test_platform_name_is_not_a_creative_owner(self):
        one_host_many_owners(self.root)
        change_candidates(self.root, lambda rows: rows[0]["provenance_check"].update(accountable_owner="  YouTube  "))
        sync_provenance_observations(self.root)
        creative_metrics(self.root)
        self.failed("DIVERSITY-01", "hosting platform or unknown owner")

    def test_origin_count_cannot_be_inflated(self):
        one_host_many_owners(self.root)
        change_json(self.root, SELECTED, lambda d: d["diversity_policy"].update(distinct_accountable_origins=21))
        change_json(self.root, REPORT, lambda d: d["diversity"].update(distinct_accountable_origins=21))
        self.failed("DIVERSITY-01", "does not equal computed 20")

    def test_platform_domain_is_not_a_creative_owner(self):
        one_host_many_owners(self.root)
        change_candidates(self.root, lambda rows: rows[0]["provenance_check"].update(accountable_owner="youtube.com"))
        sync_provenance_observations(self.root)
        creative_metrics(self.root)
        self.failed("DIVERSITY-01", "hosting platform or unknown owner")

    def test_case_and_whitespace_aliases_do_not_inflate_owner_diversity(self):
        one_host_many_owners(self.root)
        ids = {c["candidate_id"] for c in read_json(self.root / SELECTED)["items"]}
        def edit(rows):
            for index, row in enumerate(rows):
                if row["candidate_id"] in ids:
                    row["provenance_check"]["accountable_owner"] = "  ONE OWNER  " if index % 2 else "one   owner"
        change_candidates(self.root, edit)
        sync_provenance_observations(self.root)
        creative_metrics(self.root)
        self.failed("DIVERSITY-01", "diversity violations require")

    def test_owner_claim_cannot_change_without_bound_observation(self):
        one_host_many_owners(self.root)
        change_candidates(self.root, lambda rows: rows[0]["provenance_check"].update(accountable_owner="Invented owner"))
        self.failed("PROVENANCE-01", "provenance")

    def test_legacy_domain_profile_still_rejects_concentrated_hosting(self):
        one_host_many_owners(self.root)
        def intent_edit(d):
            for key in ("profile", "min_accountable_origins", "max_per_accountable_origin"):
                d["diversity_requirements"].pop(key)
        change_intent(self.root, intent_edit)
        for relative, key in ((SELECTED, "diversity_policy"), (REPORT, "diversity"), (REVIEW, "metrics")):
            def edit(d, key=key):
                for field in ("profile", "distinct_accountable_origins", "max_per_accountable_origin"):
                    d[key].pop(field, None)
            change_json(self.root, relative, edit)
        # The legacy JSON schema also enforces its domain thresholds, so this
        # compatibility test intentionally permits its schema gate to fire.
        findings = seal(self.root)["findings"]
        self.assertTrue(findings)
        self.assertTrue({f["code"] for f in findings}.issubset({"SCHEMA-01", "DIVERSITY-01"}), findings)
        self.assertFalse(any("sha256" in f["message"] for f in findings), findings)


if __name__ == "__main__":
    unittest.main(verbosity=2)
