import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
VALIDATOR = SKILL_DIR / "scripts" / "validate_tvc_reference_report.py"


def run_validator(payload: str, suffix: str):
    with tempfile.NamedTemporaryFile("w", suffix=suffix, delete=False, encoding="utf-8") as handle:
        handle.write(payload)
        path = Path(handle.name)
    try:
        return subprocess.run(
            [sys.executable, str(VALIDATOR), str(path)],
            text=True,
            capture_output=True,
            check=False,
        )
    finally:
        path.unlink(missing_ok=True)


class ValidateTvcReferenceReportTests(unittest.TestCase):
    def test_valid_json_report_passes(self):
        report = {
            "schema_version": "tvc_reference_video_evidence.v1",
            "audit": {
                "route_decision": "video_reference",
                "query_lanes": ["direct_category", "creator_source"],
                "queries_tried": ["site:vimeo.com body oil campaign film -review"],
                "platforms_checked": ["Vimeo", "YouTube"],
                "hard_exclusions": ["review", "tutorial", "showreel"],
                "verification_methods_used": ["browser"],
                "counts": {"verified": 1, "rejected": 1},
                "next_searches": ["director portfolio recovery"],
            },
            "references": [
                {
                    "rank": 1,
                    "candidate_status": "verified",
                    "title": "Example Body Oil TVC",
                    "source_url": "https://vimeo.com/example",
                    "video_kind": "single_work",
                    "brief_fit": "direct_category",
                    "reference_role": "model_application; texture_proof",
                    "visual_mechanism": "window-lit skin highlight and oil texture macro",
                    "temporal_mechanism": "need to ritual to packshot",
                    "shoot_takeaway": "Use controlled hand application before product reveal.",
                    "do_not_copy": "Do not copy the exact scene order.",
                    "risks_or_limits": "Example row for validation.",
                    "confidence": "verified",
                }
            ],
        }

        result = run_validator(json.dumps(report), ".json")

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertIn("OK", result.stdout)

    def test_json_report_rejects_unconfirmed_ranked_reference(self):
        report = {
            "schema_version": "tvc_reference_video_evidence.v1",
            "audit": {
                "route_decision": "video_reference",
                "query_lanes": ["direct_category"],
                "queries_tried": ["body oil commercial"],
                "platforms_checked": ["YouTube"],
                "hard_exclusions": ["review"],
                "verification_methods_used": ["search_snippet_only"],
                "counts": {"unconfirmed_leads": 1},
                "next_searches": ["official source recovery"],
            },
            "references": [
                {
                    "rank": 1,
                    "candidate_status": "unconfirmed_lead",
                    "title": "Possibly Useful Upload",
                    "source_url": "https://youtube.com/watch?v=example",
                    "video_kind": "single_work",
                    "brief_fit": "direct_category",
                    "reference_role": "texture_proof",
                    "visual_mechanism": "oil macro",
                    "temporal_mechanism": "unknown",
                    "shoot_takeaway": "unknown",
                    "do_not_copy": "unknown",
                    "risks_or_limits": "search snippet only",
                    "confidence": "unconfirmed_lead",
                }
            ],
        }

        result = run_validator(json.dumps(report), ".json")

        self.assertEqual(result.returncode, 1)
        self.assertIn("unconfirmed_lead", result.stdout)

    def test_json_report_rejects_showreel_as_final_reference(self):
        report = {
            "schema_version": "tvc_reference_video_evidence.v1",
            "audit": {
                "route_decision": "video_reference",
                "query_lanes": ["creator_source"],
                "queries_tried": ["beauty director showreel"],
                "platforms_checked": ["Vimeo"],
                "hard_exclusions": ["showreel"],
                "verification_methods_used": ["browser"],
                "counts": {"verified": 1},
                "next_searches": ["single work page recovery"],
            },
            "references": [
                {
                    "rank": 1,
                    "candidate_status": "verified",
                    "title": "Beauty Reel",
                    "source_url": "https://vimeo.com/reel",
                    "video_kind": "showreel",
                    "brief_fit": "craft_analogy",
                    "reference_role": "lighting",
                    "visual_mechanism": "premium fragments",
                    "temporal_mechanism": "montage",
                    "shoot_takeaway": "unclear",
                    "do_not_copy": "everything",
                    "risks_or_limits": "not a single work",
                    "confidence": "verified",
                }
            ],
        }

        result = run_validator(json.dumps(report), ".json")

        self.assertEqual(result.returncode, 1)
        self.assertIn("showreel", result.stdout)

    def test_markdown_report_requires_search_audit(self):
        markdown = """
# TVC Reference Report

## Ranked TVC References

| Rank | Status | Reference | Source URL | Fit | Reference Role | What To Borrow | Do Not Copy | Risk |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | verified | Example Body Oil TVC | https://vimeo.com/example | direct | texture_proof | oil macro | exact scene | none |
"""

        result = run_validator(markdown, ".md")

        self.assertEqual(result.returncode, 1)
        self.assertIn("Search Audit", result.stdout)

    def test_valid_markdown_report_passes(self):
        markdown = """
# TVC Reference Report

## Ranked TVC References

| Rank | Status | Reference | Source URL | Duration | Fit | Reference Role | What To Borrow | Do Not Copy | Risk |
| ---: | --- | --- | --- | ---: | --- | --- | --- | --- | --- |
| 1 | verified | Example Body Oil TVC | https://vimeo.com/example | 30s | direct_category | texture_proof | window-lit oil macro | exact scene order | none |

## Search Audit

- Route: `video_reference`
- Query lanes: direct_category, creator_source
- Queries tried: site:vimeo.com body oil campaign film -review
- Platforms checked: Vimeo, YouTube
- Hard exclusions: reviews, tutorials, showreels
- Verification: browser
- Missing tiers: none
- Next searches: director portfolio recovery
"""

        result = run_validator(markdown, ".md")

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertIn("OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
