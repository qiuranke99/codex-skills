import tempfile
import unittest
from pathlib import Path


class ReportValidatorTests(unittest.TestCase):
    def test_image_reference_report_without_pack_fails(self):
        from scripts.validate_reference_report import validate_report

        report = """# Reference research
route: `image_reference`

本轮按 source_url-first 研究完成，未下载媒体、未建本地参考包。
"""

        with tempfile.TemporaryDirectory() as tmp:
            report_path = Path(tmp) / "report.md"
            report_path.write_text(report, encoding="utf-8")

            result = validate_report(report_path)

        self.assertFalse(result["ok"])
        self.assertIn("missing_image_pack_path", result["errors"])
        self.assertIn("declares_no_download", result["errors"])

    def test_image_reference_report_with_pack_path_and_summary_passes(self):
        from scripts.validate_reference_report import validate_report

        report = """# Reference research
route: `image_reference`

image_pack_path: `reference-packs/demo-20260616-1200`
image_pack_summary: source_count=3, candidate_count=4, downloaded_count=2, failed_count=1, skipped_count=1
"""

        with tempfile.TemporaryDirectory() as tmp:
            report_path = Path(tmp) / "report.md"
            report_path.write_text(report, encoding="utf-8")

            result = validate_report(report_path)

        self.assertTrue(result["ok"])
        self.assertEqual(result["errors"], [])

    def test_explicit_links_only_report_requires_validator_override(self):
        from scripts.validate_reference_report import validate_report

        report = """# Reference research
route: `image_reference`

用户明确要求 links-only / no-download，本轮只返回 source_url。
"""

        with tempfile.TemporaryDirectory() as tmp:
            report_path = Path(tmp) / "report.md"
            report_path.write_text(report, encoding="utf-8")

            without_override = validate_report(report_path)
            with_override = validate_report(report_path, allow_links_only=True)

        self.assertFalse(without_override["ok"])
        self.assertIn("declares_links_only_without_explicit_override", without_override["errors"])
        self.assertTrue(with_override["ok"])
        self.assertEqual(with_override["errors"], [])


if __name__ == "__main__":
    unittest.main()
