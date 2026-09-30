#!/usr/bin/env python3
"""Synthetic mechanical regression only; no real video or aesthetic claims."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from scan_prompt import scan, write_new_report


class PromptScanTests(unittest.TestCase):
    def test_all_four_requested_candidates_are_located(self):
        text = "S01：微横移\nS02：小幅升高\nS03：轻后撤\nS04：缓慢升高\n"
        result = scan(text.encode())
        hits = result["candidate_mentions"]
        self.assertEqual([h["line"] for h in hits], [1, 2, 3, 4])
        self.assertEqual(len(result["explicit_shot_markers"]), 4)
        for hit in hits:
            self.assertEqual(text.splitlines()[hit["line"] - 1][hit["column"] - 1:][:len(hit["text"])], hit["text"])

    def test_negation_and_examples_never_become_confirmed_failures(self):
        result = scan('约束：禁止微横移。反例：“轻后撤”。'.encode())
        self.assertEqual(len(result["candidate_mentions"]), 2)
        self.assertTrue(all(h["disposition"] == "unreviewed_mention" for h in result["candidate_mentions"]))
        self.assertEqual(result["status"], "NEEDS_SEMANTIC_REVIEW")

    def test_no_hit_does_not_certify_quality_or_music(self):
        result = scan('一个物体一直停着。'.encode())
        self.assertEqual(result["candidate_mentions"], [])
        self.assertEqual(result["status"], "NEEDS_SEMANTIC_REVIEW")
        self.assertEqual(result["coverage"]["semantic_review"], "not_performed")
        self.assertEqual(result["coverage"]["music_listening"], "not_performed")

    def test_generic_music_is_only_a_mention(self):
        result = scan('配乐：高级 BGM。'.encode())
        self.assertTrue(result["candidate_mentions"])
        self.assertTrue(all(h["disposition"] == "unreviewed_mention" for h in result["candidate_mentions"]))

    def test_utf8_bom_crlf_and_hash_are_byte_faithful(self):
        raw = b'\xef\xbb\xbf' + 'S01：微横移\r\nS02：全景推进到特写'.encode()
        result = scan(raw)
        self.assertEqual(result["input_sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(result["explicit_shot_markers"][1]["line"], 2)

    def test_stale_version_is_rejected(self):
        previous = scan(b'first')['input_sha256']
        with self.assertRaisesRegex(ValueError, 'version mismatch'):
            scan(b'second', previous)
        self.assertEqual(scan(b'first', previous.upper())['input_sha256'], previous)

    def test_blank_bad_encoding_and_bad_digest_are_rejected(self):
        for raw in (b'', b' \r\n\t', b'\xef\xbb\xbf'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                scan(raw)
        with self.assertRaises(UnicodeError):
            scan(b'\xff')
        with self.assertRaises(ValueError):
            scan(b'hello', 'not-a-digest')

    def test_markdown_chinese_and_duplicate_markers_remain_visible(self):
        result = scan('## 镜头一：全景\n- **Shot 2** 近景\nS03 | 全景\nS03 | 近景'.encode())
        self.assertEqual(len(result['explicit_shot_markers']), 4)
        self.assertEqual(result['coverage']['all_shots_identified'], 'unverified')

    def test_english_and_scale_lock_candidates(self):
        result = scan(b'Shot 1: gently dolly back, fixed composition.')
        self.assertEqual({h['category'] for h in result['candidate_mentions']},
                         {'weak_camera_wording', 'possible_scale_or_frame_lock'})

    def test_never_overwrite_prompt_or_previous_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, target = Path(tmp) / 'prompt.md', Path(tmp) / 'report.json'
            source.write_bytes(b'original')
            report = scan(source.read_bytes())
            with self.assertRaises(ValueError):
                write_new_report(source, report, source)
            write_new_report(target, report, source)
            before = target.read_bytes()
            with self.assertRaises(ValueError):
                write_new_report(target, report, source)
            self.assertEqual(target.read_bytes(), before)
            self.assertEqual(source.read_bytes(), b'original')

    def test_cli_success_and_missing_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, target = Path(tmp) / '提示词.md', Path(tmp) / 'report.json'
            source.write_text('S01：产品近景，轻后撤。', encoding='utf-8')
            script = str(Path(__file__).with_name('scan_prompt.py'))
            result = subprocess.run([sys.executable, '-X', 'utf8', script, str(source), '--out', str(target)],
                                    capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(target.read_text(encoding='utf-8'))['status'], 'NEEDS_SEMANTIC_REVIEW')
            failed = subprocess.run([sys.executable, '-X', 'utf8', script, str(Path(tmp) / 'missing.md')],
                                    capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(failed.returncode, 2)
            self.assertEqual(json.loads(failed.stderr)['status'], 'INVALID_INPUT_OR_OUTPUT')


if __name__ == '__main__':
    unittest.main(verbosity=2)
