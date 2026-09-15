#!/usr/bin/env python3
"""Synthetic file/record tests; not a visual or independent business audit."""
from __future__ import annotations

import copy
import importlib.util
import json
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("delivery_check", PACKAGE / "scripts" / "check_delivery.py")
check = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(check)


def png(width: int, height: int) -> bytes:
    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
    rows = (b"\x00" + b"\x20\x80\xa0" * width) * height
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b""))


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.write("inputs/brief.txt", "Synthetic requested output: one 8x10 PNG with exact product identity.")
        self.write("inputs/product.txt", "Synthetic product facts for tests; not an actual brand.")
        self.write("output/hero.png", png(8, 10))
        self.write("evidence/inspection.txt", "Synthetic inspection fixture, not a claim of actual human visual review.")
        self.contract = {
            "schema_version": "brand-delivery-contract.v1",
            "project": "Synthetic delivery test",
            "independent_review_required": False,
            "user_review_required": False,
            "inputs": [
                {"id": "brief", "role": "brief", "status": "provided", **self.ref("inputs/brief.txt")},
                {"id": "product", "role": "product", "status": "provided", **self.ref("inputs/product.txt")},
            ],
            "requirements": [{
                "id": "hero", "kind": "image", "purpose": "Synthetic mechanism test",
                "source_input_ids": ["brief", "product"], "contains_text": True,
                "required_checks": ["brand", "product", "copy", "craft", "composition"],
                "spec": {"width": 8, "height": 10, "extension": ".png"},
            }],
        }
        self.write_json("contract.json", self.contract)
        self.digest = check.inputs_digest(self.contract, self.contract["requirements"][0])
        self.probe = {
            "artifact_sha256": self.ref("output/hero.png")["sha256"],
            "passed": True, "method": "synthetic fixture header verification",
            "observed": {"width": 8, "height": 10, "extension": ".png"},
        }
        self.review = {
            "kind": "self", "reviewer": "synthetic-executor",
            "artifact_sha256": self.ref("output/hero.png")["sha256"],
            "inputs_digest": self.digest, "method": "visual",
            "recorded_at": "2026-01-02T12:00:00+00:00",
            "checks": {name: {"result": "pass", "observation": "Synthetic observation for record-check testing."}
                       for name in self.contract["requirements"][0]["required_checks"]},
            "evidence": [self.ref("evidence/inspection.txt")],
            "limitations": [],
        }
        self.write_json("records/technical.json", self.probe)
        self.write_json("records/review.json", self.review)
        self.manifest = {
            "schema_version": "brand-delivery-manifest.v1",
            "contract": self.ref("contract.json"),
            "outputs": [{
                "id": "hero", "creator": "synthetic-executor",
                "file": self.ref("output/hero.png"), "inputs_digest": self.digest,
                "technical": self.ref("records/technical.json"),
                "review": self.ref("records/review.json"),
            }],
            "user_acceptance": {"status": "not_requested"},
        }
        self.save_manifest()

    def tearDown(self):
        self.temp.cleanup()

    def write(self, rel, content):
        target = self.root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            target.write_bytes(content)
        else:
            target.write_text(content, encoding="utf-8")

    def write_json(self, rel, data):
        self.write(rel, json.dumps(data, ensure_ascii=False, indent=2))

    def ref(self, rel):
        return {"path": rel, "sha256": check.sha256(self.root / rel)}

    def save_manifest(self):
        self.write_json("delivery.json", self.manifest)

    def save_review(self):
        self.write_json("records/review.json", self.review)
        self.manifest["outputs"][0]["review"] = self.ref("records/review.json")
        self.save_manifest()

    def save_contract(self, *, rebind=False):
        self.write_json("contract.json", self.contract)
        self.manifest["contract"] = self.ref("contract.json")
        if rebind:
            self.digest = check.inputs_digest(self.contract, self.contract["requirements"][0])
            self.manifest["outputs"][0]["inputs_digest"] = self.digest
            self.review["inputs_digest"] = self.digest
            self.save_review()
        self.save_manifest()

    def result(self):
        return check.check_delivery(self.root, self.root / "contract.json", self.root / "delivery.json")

    def assert_rejected(self, fragment=None):
        result = self.result()
        self.assertEqual(result["status"], "check_failed", result)
        if fragment:
            self.assertIn(fragment, json.dumps(result["errors"], ensure_ascii=False))

    def make_independent(self):
        self.contract["independent_review_required"] = True
        self.save_contract(rebind=True)
        first = copy.deepcopy(self.review)
        first.update(kind="first_independent_review", reviewer="synthetic-reviewer",
                     participated_in_production=False, exposure="none",
                     recorded_at="2026-01-02T11:00:00+00:00")
        self.write_json("records/first.json", first)
        self.review.update(kind="independent", reviewer="synthetic-reviewer",
                           first_review=self.ref("records/first.json"))
        self.save_review()
        return first

    def test_valid_records_do_not_claim_visual_or_user_approval(self):
        result = self.result()
        self.assertEqual(result["status"], "delivery_files_and_records_valid", result)
        self.assertEqual(result["user_acceptance"], "not_requested")
        self.assertTrue(result["limits"])

    def test_critical_failure_cannot_be_overridden_by_score(self):
        self.review["score"] = 35
        self.review["checks"]["product"]["result"] = "fail"
        self.save_review()
        self.assert_rejected("product=fail")

    def test_unverified_is_not_pass(self):
        self.review["checks"]["copy"]["result"] = "unverified"
        self.save_review()
        self.assert_rejected("copy=unverified")

    def test_extra_unresolved_check_also_blocks_delivery(self):
        self.review["checks"]["additional_issue"] = {"result": "fail", "observation": "Synthetic extra defect"}
        self.save_review()
        self.assert_rejected("additional_issue")

    def test_missing_required_output(self):
        extra = copy.deepcopy(self.contract["requirements"][0])
        extra["id"] = "second-sku"
        self.contract["requirements"].append(extra)
        self.save_contract()
        self.assert_rejected("missing")

    def test_extra_output_does_not_substitute_for_requested_one(self):
        self.manifest["outputs"][0]["id"] = "unrequested"
        self.save_manifest()
        self.assert_rejected("coverage mismatch")

    def test_duplicate_output_ids(self):
        self.manifest["outputs"].append(copy.deepcopy(self.manifest["outputs"][0]))
        self.save_manifest()
        self.assert_rejected("duplicate IDs")

    def test_empty_delivery_is_not_complete(self):
        self.manifest["outputs"] = []
        self.save_manifest()
        self.assert_rejected("non-empty")

    def test_output_changed_after_review(self):
        self.write("output/hero.png", png(9, 10))
        self.assert_rejected("file hash changed")

    def test_rebinding_file_does_not_reuse_old_review(self):
        self.write("output/hero.png", png(8, 10) + b"changed")
        self.manifest["outputs"][0]["file"] = self.ref("output/hero.png")
        self.probe["artifact_sha256"] = self.ref("output/hero.png")["sha256"]
        self.write_json("records/technical.json", self.probe)
        self.manifest["outputs"][0]["technical"] = self.ref("records/technical.json")
        self.save_manifest()
        self.assert_rejected("review targets stale output")

    def test_input_bytes_changed(self):
        self.write("inputs/product.txt", "Changed synthetic SKU.")
        self.assert_rejected("file hash changed")

    def test_updated_input_manifest_invalidates_old_output_binding(self):
        self.write("inputs/product.txt", "Changed synthetic SKU.")
        self.contract["inputs"][1].update(self.ref("inputs/product.txt"))
        self.save_contract()
        self.assert_rejected("stale inputs")

    def test_unrelated_input_change_does_not_stale_unrelated_review(self):
        self.write("inputs/unrelated.txt", "A different unused campaign.")
        self.contract["inputs"].append({
            "id": "unused", "role": "scene", "status": "provided", **self.ref("inputs/unrelated.txt")
        })
        self.save_contract()
        self.assertEqual(self.result()["status"], "delivery_files_and_records_valid")

    def test_rejected_input_cannot_be_active(self):
        self.contract["inputs"][1]["status"] = "rejected"
        self.save_contract(rebind=True)
        self.assert_rejected("rejected input is active")

    def test_original_brief_cannot_be_omitted(self):
        self.contract["requirements"][0]["source_input_ids"] = ["product"]
        self.save_contract(rebind=True)
        self.assert_rejected("original brief")

    def test_product_check_cannot_be_removed(self):
        self.contract["requirements"][0]["required_checks"].remove("product")
        self.save_contract(rebind=True)
        self.assert_rejected("mandatory")

    def test_review_cannot_omit_a_required_check(self):
        del self.review["checks"]["copy"]
        self.save_review()
        self.assert_rejected("omitted")

    def test_blank_observation_is_rejected(self):
        self.review["checks"]["craft"]["observation"] = " "
        self.save_review()
        self.assert_rejected("observation")

    def test_unresolved_limitations_block_delivery(self):
        self.review["limitations"] = ["Synthetic unreadable label."]
        self.save_review()
        self.assert_rejected("limitations")

    def test_missing_evidence_blocks_delivery(self):
        self.review["evidence"] = []
        self.save_review()
        self.assert_rejected("evidence")

    def test_evidence_change_is_detected(self):
        self.write("evidence/inspection.txt", "Changed evidence.")
        self.assert_rejected("file hash changed")

    def test_png_dimensions_are_rechecked(self):
        self.write("output/hero.png", png(12, 10))
        artifact = self.ref("output/hero.png")
        self.manifest["outputs"][0]["file"] = artifact
        self.probe["artifact_sha256"] = artifact["sha256"]
        self.review["artifact_sha256"] = artifact["sha256"]
        self.write_json("records/technical.json", self.probe)
        self.manifest["outputs"][0]["technical"] = self.ref("records/technical.json")
        self.save_review()
        self.assert_rejected("actual PNG dimensions")

    def test_invalid_png_header_is_rejected(self):
        self.write("output/hero.png", b"This is not a PNG file.")
        artifact = self.ref("output/hero.png")
        self.manifest["outputs"][0]["file"] = artifact
        self.probe["artifact_sha256"] = artifact["sha256"]
        self.write_json("records/technical.json", self.probe)
        self.manifest["outputs"][0]["technical"] = self.ref("records/technical.json")
        self.save_manifest()
        self.assert_rejected("invalid PNG")

    def test_probe_spec_mismatch(self):
        self.probe["observed"]["width"] = 9
        self.write_json("records/technical.json", self.probe)
        self.manifest["outputs"][0]["technical"] = self.ref("records/technical.json")
        self.save_manifest()
        self.assert_rejected("spec mismatch")

    def test_image_method_cannot_validate_video(self):
        requirement = self.contract["requirements"][0]
        requirement["kind"] = "video"
        requirement["required_checks"].append("motion")
        requirement["spec"]["duration"] = 1
        self.review["checks"]["motion"] = {"result": "pass", "observation": "Synthetic check."}
        self.probe["observed"]["duration"] = 1
        self.write_json("records/technical.json", self.probe)
        self.manifest["outputs"][0]["technical"] = self.ref("records/technical.json")
        self.save_contract(rebind=True)
        self.assert_rejected("method mismatches media")

    def test_parent_path_is_rejected(self):
        self.manifest["outputs"][0]["file"]["path"] = "../outside.png"
        self.save_manifest()
        self.assert_rejected("parent traversal")

    def test_absolute_path_is_rejected(self):
        self.manifest["outputs"][0]["file"]["path"] = str(self.root / "output" / "hero.png")
        self.save_manifest()
        self.assert_rejected("project-relative")

    def test_duplicate_json_key_is_rejected(self):
        self.write("delivery.json", '{"schema_version":"a","schema_version":"b"}')
        self.assert_rejected("duplicate JSON key")

    def test_same_bytes_cannot_impersonate_different_skus(self):
        extra = copy.deepcopy(self.contract["requirements"][0])
        extra["id"] = "sku-b"
        self.contract["requirements"].append(extra)
        output = copy.deepcopy(self.manifest["outputs"][0])
        output["id"] = "sku-b"
        output["inputs_digest"] = check.inputs_digest(self.contract, extra)
        self.manifest["outputs"].append(output)
        self.save_contract()
        self.assert_rejected("same file bytes")

    def test_user_review_pending_is_not_user_accepted(self):
        self.contract["user_review_required"] = True
        self.manifest["user_acceptance"]["status"] = "pending"
        self.save_contract()
        result = self.result()
        self.assertEqual(result["status"], "delivery_files_and_records_valid")
        self.assertEqual(result["user_acceptance"], "pending")

    def test_required_user_review_cannot_be_discarded(self):
        self.contract["user_review_required"] = True
        self.save_contract()
        self.assert_rejected("user review was discarded")

    def test_user_acceptance_requires_evidence(self):
        self.manifest["user_acceptance"]["status"] = "accepted"
        self.save_manifest()
        self.assert_rejected("file reference")

    def test_user_acceptance_exact_version_is_checked(self):
        self.write_json("records/user.json", {
            "approved_by": "synthetic-user", "source": "synthetic acceptance fixture",
            "contract_sha256": self.ref("contract.json")["sha256"],
            "accepted_outputs": {"hero": "0" * 64},
        })
        self.manifest["user_acceptance"] = {"status": "accepted", "record": self.ref("records/user.json")}
        self.save_manifest()
        self.assert_rejected("exact outputs")

    def test_independent_review_cannot_be_replaced_by_self_review(self):
        self.contract["independent_review_required"] = True
        self.save_contract(rebind=True)
        self.assert_rejected("independent review is still required")

    def test_independent_records_are_checked_without_claiming_independence(self):
        self.make_independent()
        result = self.result()
        self.assertEqual(result["status"], "delivery_files_and_records_valid", result)
        self.assertTrue(any("independence" in x for x in result["limits"]))

    def test_creator_cannot_claim_independent_review(self):
        self.make_independent()
        self.review["reviewer"] = "synthetic-executor"
        self.save_review()
        self.assert_rejected("creator cannot claim")

    def test_exposed_first_reviewer_is_rejected(self):
        first = self.make_independent()
        first["exposure"] = "exposed"
        self.write_json("records/first.json", first)
        self.review["first_review"] = self.ref("records/first.json")
        self.save_review()
        self.assert_rejected("prior explanation exposure")

    def test_late_first_review_is_rejected(self):
        first = self.make_independent()
        first["recorded_at"] = "2026-01-02T13:00:00+00:00"
        self.write_json("records/first.json", first)
        self.review["first_review"] = self.ref("records/first.json")
        self.save_review()
        self.assert_rejected("must precede")

    def test_changed_independent_decision_requires_reason(self):
        first = self.make_independent()
        first["checks"]["craft"]["result"] = "fail"
        self.write_json("records/first.json", first)
        self.review["first_review"] = self.ref("records/first.json")
        self.save_review()
        self.assert_rejected("no reason")

    def test_checker_is_read_only(self):
        before = {p.relative_to(self.root).as_posix(): check.sha256(p) for p in self.root.rglob("*") if p.is_file()}
        self.result()
        after = {p.relative_to(self.root).as_posix(): check.sha256(p) for p in self.root.rglob("*") if p.is_file()}
        self.assertEqual(before, after)

    def test_cli_check_and_digest(self):
        script = PACKAGE / "scripts" / "check_delivery.py"
        for command in [
            [sys.executable, "-B", str(script), "check", "--root", str(self.root)],
            [sys.executable, "-B", str(script), "inputs-digest", "--root", str(self.root), "--output-id", "hero"],
        ]:
            result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", check=False)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIsInstance(json.loads(result.stdout), dict)


if __name__ == "__main__":
    unittest.main(verbosity=2)
