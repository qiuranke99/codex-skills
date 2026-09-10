#!/usr/bin/env python3
"""Portable mechanical regression tests. All fixture files use system temp."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

sys.dont_write_bytecode = True
import check_delivery as checker


SCRIPT = Path(__file__).with_name("check_delivery.py").resolve()


def timeline(shots=None, hold_start=28.5):
    return {"shots": shots if shots is not None else [
        {"id": "S01", "start": 0, "end": 2.5},
        {"id": "S02", "start": 2.5, "end": 9.75},
        {"id": "S03", "start": 9.75, "end": 30},
    ], "hold_start": hold_start}


class DeliveryChecks(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="tvc-delivery-test-")
        self.addCleanup(self.temporary.cleanup)
        self.temp = Path(self.temporary.name)

    def fixture(self, name, content):
        path = self.temp / name
        path.write_bytes(content if isinstance(content, bytes) else content.encode("utf-8"))
        return path

    def check_timeline(self, payload):
        path = self.fixture("timeline.json", json.dumps(payload))
        return checker.check_timeline(checker.read_timeline(path))

    def cli(self, *args, expected=0):
        completed = subprocess.run(
            [sys.executable, "-E", "-s", "-B", str(SCRIPT), *map(str, args)],
            cwd=self.temp, capture_output=True, text=True, encoding="utf-8", timeout=10,
        )
        self.assertEqual(completed.returncode, expected, completed.stdout + completed.stderr)
        self.assertNotIn("Traceback", completed.stdout + completed.stderr)
        self.assertEqual(completed.stderr, "")
        return json.loads(completed.stdout)

    def test_unicode_codepoints_utf16_and_raw_bytes(self):
        # Emoji is two UTF-16 units; a combining accent remains another codepoint.
        raw = "\ufeff中😀e\u0301\r\n ".encode("utf-8")
        path = self.fixture("正文.txt", raw)
        result = checker.check_prompt(path)
        self.assertEqual(result["codepoints"], 8)
        self.assertEqual(result["utf16_units"], 9)
        self.assertEqual(result["utf8_bytes"], len(raw))
        self.assertIsNone(result["within_limit"])

    def test_prompt_boundary_and_reserve(self):
        path = self.fixture("body.txt", "12345")
        self.assertTrue(checker.check_prompt(path, 7, 2)["passed"])
        self.assertFalse(checker.check_prompt(path, 7, 3)["passed"])

    def test_count_units_change_independent_decision(self):
        path = self.fixture("body.txt", "中😀")
        self.assertTrue(checker.check_prompt(path, 2, count_unit="codepoints")["passed"])
        self.assertFalse(checker.check_prompt(path, 2, count_unit="utf16")["passed"])

    def test_legal_variable_shot_lengths(self):
        self.assertTrue(self.check_timeline(timeline())["passed"])

    def test_single_shot_and_exact_one_second_hold(self):
        payload = timeline([{"id": "one", "start": 0, "end": 30}], 29)
        self.assertTrue(self.check_timeline(payload)["passed"])

    def test_hold_may_start_at_last_shot_start(self):
        payload = timeline([
            {"id": "one", "start": 0, "end": 29},
            {"id": "two", "start": 29, "end": 30},
        ], 29)
        self.assertTrue(self.check_timeline(payload)["passed"])

    def test_decimal_endpoints_are_not_binary_floats(self):
        path = self.fixture("exact.json", '{"shots":['
                            '{"id":"a","start":0,"end":0.3},'
                            '{"id":"b","start":0.30,"end":30}],"hold_start":29}')
        payload = checker.read_timeline(path)
        self.assertIsInstance(payload["shots"][0]["end"], Decimal)
        self.assertTrue(checker.check_timeline(payload)["passed"])

    def test_long_decimal_gap_is_not_rounded_away(self):
        path = self.fixture("precise.json", '{"shots":['
                            '{"id":"a","start":0,"end":0.3},'
                            '{"id":"b","start":0.300000000000000000000000000001,"end":30}],'
                            '"hold_start":29}')
        result = checker.check_timeline(checker.read_timeline(path))
        self.assertFalse(result["passed"])
        self.assertIn("gap", " ".join(result["errors"]))

    def test_long_decimal_hold_below_one_second_fails(self):
        path = self.fixture("precise-hold.json", '{"shots":['
                            '{"id":"a","start":0,"end":30}],'
                            '"hold_start":29.000000000000000000000000000001}')
        self.assertFalse(checker.check_timeline(checker.read_timeline(path))["passed"])

    def test_overlap_gap_and_input_order(self):
        for start in (2.4, 2.6):
            with self.subTest(start=start):
                payload = timeline()
                payload["shots"][1]["start"] = start
                self.assertFalse(self.check_timeline(payload)["passed"])
        payload = timeline()
        payload["shots"].reverse()
        self.assertFalse(self.check_timeline(payload)["passed"])

    def test_wrong_total_length(self):
        for end in (29.9, 30.1):
            with self.subTest(end=end):
                payload = timeline()
                payload["shots"][-1]["end"] = end
                self.assertFalse(self.check_timeline(payload)["passed"])

    def test_negative_start_and_nonzero_origin(self):
        for start in (-0.1, 0.1):
            with self.subTest(start=start):
                payload = timeline()
                payload["shots"][0]["start"] = start
                self.assertFalse(self.check_timeline(payload)["passed"])

    def test_zero_or_negative_shot_duration(self):
        for end in (0, -1):
            with self.subTest(end=end):
                payload = timeline()
                payload["shots"][0]["end"] = end
                self.assertFalse(self.check_timeline(payload)["passed"])

    def test_duplicate_or_invalid_shot_ids(self):
        for shot_id in ("S01", "", "   ", None, 123):
            with self.subTest(shot_id=shot_id):
                payload = timeline()
                payload["shots"][1]["id"] = shot_id
                self.assertFalse(self.check_timeline(payload)["passed"])

    def test_hold_is_inside_last_shot_and_at_least_one_second(self):
        for hold_start in (-1, 5, 29.1, 30, 31):
            with self.subTest(hold_start=hold_start):
                self.assertFalse(self.check_timeline(timeline(hold_start=hold_start))["passed"])

    def test_boolean_string_null_are_not_numbers(self):
        for value in (True, False, "0", None):
            for field in ("start", "end", "hold_start"):
                with self.subTest(value=value, field=field):
                    payload = timeline()
                    if field == "hold_start":
                        payload[field] = value
                    else:
                        payload["shots"][0][field] = value
                    self.assertFalse(self.check_timeline(payload)["passed"])

    def test_nonfinite_json_numbers_rejected(self):
        for token in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(token=token):
                path = self.fixture("nan.json", '{"shots":[],"hold_start":' + token + '}')
                with self.assertRaises(checker.InputError):
                    checker.read_timeline(path)

    def test_duplicate_json_keys_rejected(self):
        path = self.fixture("duplicate.json", '{"shots":[],"hold_start":29,"hold_start":0}')
        with self.assertRaises(checker.InputError):
            checker.read_timeline(path)

    def test_incorrect_timeline_shape(self):
        for payload in ([], None, {}, {"shots": []}, {"shots": [None]},
                        {"shots": [{"id": "a"}], "hold_start":29}):
            with self.subTest(payload=payload):
                self.assertFalse(self.check_timeline(payload)["passed"])

    def test_cli_count_only_and_repeated_files_not_summed(self):
        one = self.fixture("one.txt", "1234")
        two = self.fixture("two.txt", "5678")
        self.assertIsNone(self.cli("--prompt", one)["prompts"][0]["within_limit"])
        result = self.cli("--prompt", one, "--prompt", two, "--limit", 4)
        self.assertTrue(result["passed"])
        self.assertEqual(len(result["prompts"]), 2)

    def test_cli_one_payload_exceeds_effective_limit(self):
        one = self.fixture("one.txt", "1234")
        two = self.fixture("two.txt", "12345")
        result = self.cli("--prompt", one, "--prompt", two, "--limit", 6, "--reserve", 2, expected=1)
        self.assertTrue(result["prompts"][0]["passed"])
        self.assertFalse(result["prompts"][1]["passed"])

    def test_cli_utf16(self):
        path = self.fixture("emoji.txt", "😀")
        result = self.cli("--prompt", path, "--count-unit", "utf16", "--limit", 1, expected=1)
        self.assertEqual(result["prompts"][0]["counted_units"], 2)

    def test_cli_empty_file_at_zero_effective_limit(self):
        path = self.fixture("empty.txt", "")
        self.assertTrue(self.cli("--prompt", path, "--limit", 1, "--reserve", 1)["passed"])

    def test_cli_timeline_only_and_combined(self):
        path = self.fixture("timeline.json", json.dumps(timeline()))
        self.assertTrue(self.cli("--timeline", path)["passed"])
        prompt = self.fixture("body.txt", "A")
        self.assertTrue(self.cli("--timeline", path, "--prompt", prompt, "--limit", 1)["passed"])

    def test_cli_hold_29_1_is_a_failed_check(self):
        path = self.fixture("hold.json", json.dumps(timeline(hold_start=29.1)))
        self.assertFalse(self.cli("--timeline", path, expected=1)["passed"])

    def test_cli_invalid_options_are_json_without_tracebacks(self):
        path = self.fixture("body.txt", "A")
        cases = [(), ("--unexpected",), ("--prompt",),
                 ("--prompt", path, "--limit", 0), ("--prompt", path, "--limit", -1),
                 ("--prompt", path, "--limit", "1.5"), ("--prompt", path, "--reserve", -1),
                 ("--prompt", path, "--reserve", 1),
                 ("--prompt", path, "--limit", 1, "--reserve", 2),
                 ("--prompt", path, "--count-unit", "bytes")]
        for args in cases:
            with self.subTest(args=args):
                self.assertEqual(self.cli(*args, expected=2)["error"]["kind"], "invalid_input")

    def test_cli_missing_invalid_utf8_and_invalid_json(self):
        bad_utf8 = self.fixture("bad.txt", b"\xff")
        bad_json = self.fixture("bad.json", '{"shots":')
        nan_json = self.fixture("nan.json", '{"shots":[],"hold_start":NaN}')
        duplicate = self.fixture("duplicate.json", '{"shots":[],"shots":[]}')
        for flag, path in (("--prompt", self.temp / "missing.txt"), ("--prompt", bad_utf8),
                           ("--timeline", bad_json), ("--timeline", nan_json), ("--timeline", duplicate)):
            with self.subTest(path=path):
                self.assertFalse(self.cli(flag, path, expected=2)["passed"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
