#!/usr/bin/env python3
"""Opt-in wave and four-identity regressions; synthetic temporary fixtures only."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from datetime import datetime, timezone
from _contract_utils import read_json, read_jsonl, write_json, write_jsonl
from _evidence_binding import approach_plan_sha256, approach_registration_bindings, approach_wave_sha256
from register_search_wave import append_wave
from test_contract import make_valid_run, _refresh_approach_plan_bindings, _refresh_report_contracts, _convert_contract_simulation
from validate_research_run import validate_run, PackValidator
from build_review_gallery import build_gallery


def capacity_fixture(root):
    make_valid_run(root)
    mapping = {**{f"finder_{i}": "B" for i in range(10)},
               **{f"capture_operator_{i}": "A" for i in range(10)},
               **{f"verifier_{i}": "C" for i in range(10)},
               "root": "A", "curator_relevance": "B", "curator_diversity": "C", "auditor_red": "D"}
    def remap(x):
        if isinstance(x, str): return mapping.get(x, x)
        if isinstance(x, dict): return {k: remap(v) for k, v in x.items()}
        if isinstance(x, list):
            values = [remap(v) for v in x]
            return list(dict.fromkeys(values)) if all(isinstance(v, str) for v in values) else values
        return x
    for file in root.rglob("*.json"):
        write_json(file, remap(read_json(file)))
    for file in root.rglob("*.jsonl"):
        write_jsonl(file, [remap(v) for v in read_jsonl(file)])
    file = root / "01_orchestration/approach_registry.json"
    reg = read_json(file)
    reg["agents"] = [
        {"agent_id": aid, "role": roles[0], "additional_roles": roles[1:], "access_scope": ["public"], "session_owner": False}
        for aid, roles in [("A", ["root_synthesizer", "capture_operator"]),
                           ("B", ["search_scout", "credit_graph_scout", "relevance_curator"]),
                           ("C", ["verification_agent", "diversity_curator"]), ("D", ["adversarial_auditor"])]]
    reg["independence_policy"].update(profile="capacity4_staged_v1", decision_roles_use_distinct_agent_ids=False)
    write_json(file, reg)
    file = root / "06_output/verification_report.json"
    report = read_json(file)
    report["agent_separation"].update(profile="capacity4_staged_v1", decision_roles_disjoint=False)
    write_json(file, report)
    _refresh_approach_plan_bindings(root)
    (root / "06_output/reference_board.html").write_text(build_gallery(root), encoding="utf-8")
    _refresh_report_contracts(root, root)


class WaveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        make_valid_run(self.root)
        self.reg = read_json(self.root / "01_orchestration/approach_registry.json")

    def tearDown(self): self.temp.cleanup()

    def draft(self, suffix="4"):
        item = copy.deepcopy(self.reg["approaches"][0])
        item.update(approach_id="new_"+suffix, started_at=None, status="planned", returned_count=0,
                    qualified_count=0, qualification_rate=0, failure_records=[], next_round_adjustment=None)
        item["queries"] = [{"query_id": "new_query_"+suffix, "query_text": "new accountable campaign hypothesis", "locale": "en", "round": 2}]
        return [item]

    def append(self, registry=None, suffix="4"):
        with patch("register_search_wave.datetime") as clock:
            clock.now.return_value = datetime(2026, 7, 13, 0, 7, int(suffix), tzinfo=timezone.utc)
            return append_wave(registry or self.reg, self.draft(suffix), wave_id="wave_"+suffix,
                               trigger="Independent access failures require a new source hypothesis.")

    def test_old_hash_and_captures_survive_two_appends(self):
        old = approach_plan_sha256(self.reg)
        first = self.append(); second = self.append(first, "5")
        self.assertEqual(old, approach_plan_sha256(second))
        bindings = approach_registration_bindings(second)
        for item in self.reg["approaches"]: self.assertEqual(bindings[item["approach_id"]][0], old)
        self.assertNotEqual(bindings["new_4"][0], bindings["new_5"][0])

    def test_old_query_rewrite_fails(self):
        reg = self.append(); reg["approaches"][0]["queries"][0]["query_text"] = "rewritten"
        with self.assertRaises(ValueError): approach_registration_bindings(reg)

    def test_wave_rewrite_parent_and_backdate_fail(self):
        for mutation in ("query", "parent", "time", "unregistered"):
            reg = self.append(); wave = reg["append_only_plan"]["waves"][0]
            if mutation == "query": reg["approaches"][-1]["queries"][0]["query_text"] = "tampered"
            if mutation == "parent": wave["parent_plan_sha256"] = "f" * 64
            if mutation == "time":
                wave["frozen_at"] = reg["registration"]["frozen_at"]
                wave["plan_sha256"] = approach_wave_sha256(reg, wave)
            if mutation == "unregistered": reg["approaches"].extend(self.draft("6"))
            with self.subTest(mutation=mutation), self.assertRaises(ValueError): approach_registration_bindings(reg)

    def test_retroactive_start_and_duplicate_query_refused(self):
        draft = self.draft(); draft[0]["started_at"] = "2026-07-13T00:06:00Z"
        with self.assertRaises(ValueError): append_wave(self.reg, draft, wave_id="w", trigger="A sufficiently long trigger reason")
        draft = self.draft(); draft[0]["queries"] = copy.deepcopy(self.reg["approaches"][0]["queries"])
        with self.assertRaises(ValueError): append_wave(self.reg, draft, wave_id="w", trigger="A sufficiently long trigger reason")

    def test_capacity_opt_in_invalidates_old_plan(self):
        reg = copy.deepcopy(self.reg)
        reg["independence_policy"].update(profile="capacity4_staged_v1", decision_roles_use_distinct_agent_ids=False)
        with self.assertRaises(ValueError): approach_registration_bindings(reg)

    def mode_validator(self):
        validator = PackValidator(self.root, self.root, {"pack_id":"image_pack","modality":"image"},
                                  Path(__file__).resolve().parent.parent/"references", datetime.now(timezone.utc))
        self.assertTrue(validator._load())
        return validator

    def test_new_wave_late_discovery_and_wrong_capture_hash_fail(self):
        _convert_contract_simulation(self.root, "production_live")
        self.reg=read_json(self.root/"01_orchestration/approach_registry.json")
        reg=self.append()
        reg["approaches"][-1]["started_at"]="2026-07-13T00:08:00Z"
        write_json(self.root/"01_orchestration/approach_registry.json",reg)
        validator=self.mode_validator(); validator._validate_mode_and_registration()
        self.assertFalse(validator.findings, [x.message for x in validator.findings])
        # Give an existing row the new approach, retaining its earlier discovery.
        validator=self.mode_validator()
        validator.artifacts["candidates"][0]["agent_trace"]["approach_id"]="new_4"
        validator.artifacts["candidates"][0]["discovered_at"]="2026-07-13T00:06:00Z"
        validator._validate_mode_and_registration()
        self.assertTrue(any(x.code=="PREREG-01" and "wave" in x.message for x in validator.findings))
        # Old base hash cannot authorize a new-wave capture.
        validator=self.mode_validator()
        validator.artifacts["captures"][0]["approach_id"]="new_4"
        validator._validate_mode_and_registration()
        self.assertTrue(any(x.code=="CAPTURE-01" for x in validator.findings))


class CapacityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.root = Path(self.temp.name)
        capacity_fixture(self.root)
    def tearDown(self): self.temp.cleanup()
    def result(self):
        _refresh_report_contracts(self.root, self.root)
        return validate_run(self.root)
    def test_four_real_identities_pass(self):
        r = self.result(); self.assertEqual(r["status"], "PASS", json.dumps(r, indent=2))
    def test_legacy_strict_still_passes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); make_valid_run(root)
            self.assertEqual(validate_run(root)["status"], "PASS")
    def test_false_disjoint_claim_rejected(self):
        p=self.root/"06_output/verification_report.json";o=read_json(p)
        o["agent_separation"]["decision_roles_disjoint"]=True;write_json(p,o)
        self.assertNotEqual(self.result()["status"], "PASS")
    def test_finder_verifier_overlap_rejected(self):
        p=self.root/"03_verification/verification_receipts.jsonl";o=read_jsonl(p)
        o[0]["verifier"]["verifier_agent_id"]="B";write_jsonl(p,o)
        self.assertNotEqual(self.result()["status"], "PASS")
    def test_curator_same_identity_rejected(self):
        p=self.root/"06_output/verification_report.json";o=read_json(p)
        o["agent_separation"]["diversity_curator_agent_id"]="B";write_json(p,o)
        self.assertNotEqual(self.result()["status"], "PASS")
    def test_auditor_operative_overlap_rejected(self):
        p=self.root/"06_output/verification_report.json";o=read_json(p)
        o["agent_separation"]["auditor_agent_id"]="A";write_json(p,o)
        self.assertNotEqual(self.result()["status"], "PASS")
    def test_auditor_role_must_be_reserved_at_plan_time(self):
        p=self.root/"01_orchestration/approach_registry.json";o=read_json(p)
        o["agents"][-1]["additional_roles"]=["search_scout"]
        o["registration"]["plan_sha256"]=approach_plan_sha256(o)
        with self.assertRaises(ValueError): approach_registration_bindings(o)

    def test_new_wave_accepts_only_capacity_finder(self):
        registry=read_json(self.root/"01_orchestration/approach_registry.json")
        original=copy.deepcopy(registry)
        draft=copy.deepcopy(registry["approaches"][0])
        draft.update(approach_id="new_capacity_lane",status="planned",started_at=None,
                     returned_count=0,qualified_count=0,qualification_rate=0,failure_records=[],next_round_adjustment=None)
        draft["queries"]=[{"query_id":"new_capacity_query","query_text":"New accountable creator population","locale":"en","round":2}]
        for actor in ("D","A","C"):
            draft["executing_agent_id"]=actor
            with self.subTest(actor=actor), self.assertRaises(ValueError):
                append_wave(registry,[draft],wave_id="new_wave",trigger="Actual access failures require another source population.")
        # Even extra authenticated-source roles cannot turn A/C into finders.
        for actor in ("A","C"):
            altered=copy.deepcopy(registry)
            next(a for a in altered["agents"] if a["agent_id"]==actor)["additional_roles"].append("authenticated_source_operator")
            altered["registration"]["plan_sha256"]=approach_plan_sha256(altered)
            draft["executing_agent_id"]=actor
            with self.subTest(auth_actor=actor), self.assertRaises(ValueError):
                append_wave(altered,[draft],wave_id="new_wave",trigger="Actual access failures require another source population.")
        draft["executing_agent_id"]="B"
        result=append_wave(registry,[draft],wave_id="new_wave",trigger="Actual access failures require another source population.")
        self.assertEqual(registry,original)
        self.assertEqual(result["agents"],original["agents"])
        self.assertEqual(result["approaches"][:-1],original["approaches"])
        self.assertEqual(result["registration"],original["registration"])
        self.assertEqual(result["approaches"][-1]["started_at"],None)
        approach_registration_bindings(result)

    def test_strict_new_wave_rejects_registered_non_scout(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);make_valid_run(root)
            registry=read_json(root/"01_orchestration/approach_registry.json")
            draft=copy.deepcopy(registry["approaches"][0])
            draft.update(approach_id="strict_bad_lane",executing_agent_id="auditor_red",status="planned",started_at=None,
                         returned_count=0,qualified_count=0,qualification_rate=0,failure_records=[],next_round_adjustment=None)
            draft["queries"]=[{"query_id":"strict_bad_query","query_text":"New source hypothesis","locale":"en","round":2}]
            with self.assertRaises(ValueError):
                append_wave(registry,[draft],wave_id="strict_bad_wave",trigger="Actual access failures require another source population.")


class ZeroYieldCoverageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.root = Path(self.temp.name)
        make_valid_run(self.root)
    def tearDown(self): self.temp.cleanup()

    def prepare(self, productive_method_count=2, mutation=None):
        path = self.root / "01_orchestration/approach_registry.json"
        registry = read_json(path)
        productive = ["direct_category", "credit_graph"][:productive_method_count]
        for index, approach in enumerate(registry["approaches"]):
            approach["method"] = productive[index % productive_method_count]
        zero_methods = ["challenger", "adjacent_discipline"][:3-productive_method_count]
        for index, method in enumerate(zero_methods):
            zero = copy.deepcopy(registry["approaches"][0])
            query_id = f"zero_query_{index}"
            zero.update(approach_id=f"zero_approach_{index}", method=method,
                        returned_count=0, qualified_count=0, qualification_rate=0,
                        status="abandoned", next_round_adjustment="Seek another accountable source population after this negative result.")
            zero["queries"] = [{"query_id":query_id,"query_text":f"Executed zero-yield hypothesis {index}","locale":"en","round":1}]
            zero["failure_records"] = [{"failure_id":f"failure_zero_{index}","query_id":query_id,
                "source_family_id":zero["source_family_ids"][0],"round":1,"failure_code":"zero_yield",
                "candidate_ids":[],"receipt_ids":[],"observed_at":"2026-07-13T00:12:00Z",
                "reason":"The actual registered source/query returned no exact candidate work.",
                "fallback_action":"Preserve this negative search result and move to a different population."}]
            registry["approaches"].append(zero)
        if mutation:
            mutation(registry["approaches"][-1])
        registry["coverage"][0].update(declared_distinct_method_count=3, covered_methods=productive+zero_methods)
        write_json(path, registry)
        _refresh_approach_plan_bindings(self.root)

    def test_thirty_candidates_from_one_productive_method_plus_two_real_empty_methods(self):
        self.prepare(1)
        result=validate_run(self.root)
        self.assertEqual(result["status"],"PASS",json.dumps(result,indent=2))
        self.assertEqual(result["packs"][0]["metrics"]["qualified"],30)

    def test_thirty_candidates_from_two_productive_methods_plus_one_real_empty_method(self):
        self.prepare(2)
        result=validate_run(self.root)
        self.assertEqual(result["status"],"PASS",json.dumps(result,indent=2))
        self.assertEqual(result["packs"][0]["metrics"]["selected"],20)

    def test_planned_lane_does_not_supply_coverage(self):
        self.prepare(mutation=lambda a:a.update(status="planned",started_at=None))
        self.assertNotEqual(validate_run(self.root)["status"],"PASS")

    def test_empty_abandoned_lane_does_not_supply_coverage(self):
        self.prepare(mutation=lambda a:a.update(failure_records=[]))
        self.assertNotEqual(validate_run(self.root)["status"],"PASS")

    def test_failure_predating_search_does_not_supply_coverage(self):
        self.prepare(mutation=lambda a:a["failure_records"][0].update(observed_at="2026-07-13T00:04:00Z"))
        self.assertNotEqual(validate_run(self.root)["status"],"PASS")

    def test_unregistered_query_failure_does_not_supply_coverage(self):
        self.prepare(mutation=lambda a:a["failure_records"][0].update(query_id="missing_query"))
        self.assertNotEqual(validate_run(self.root)["status"],"PASS")

    def test_no_next_adjustment_does_not_supply_coverage(self):
        self.prepare(mutation=lambda a:a.update(next_round_adjustment=None))
        self.assertNotEqual(validate_run(self.root)["status"],"PASS")


if __name__ == "__main__": unittest.main()
