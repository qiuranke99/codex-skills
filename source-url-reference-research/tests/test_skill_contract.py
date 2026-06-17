import unittest
from pathlib import Path


class SkillContractTests(unittest.TestCase):
    def setUp(self):
        self.skill_text = Path("SKILL.md").read_text(encoding="utf-8")

    def test_image_reference_route_requires_pack_not_link_only_output(self):
        required_phrases = [
            "MUST create a local image reference pack",
            "Do not finish an `image_reference` route with only Markdown links",
            "Run `scripts/build_image_reference_pack.py`",
            "source_url-first does not mean source_url-only",
            "Run `scripts/validate_reference_report.py` before the final answer",
            "If no image can be downloaded, still create the pack directory and manifest",
        ]

        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.skill_text)


if __name__ == "__main__":
    unittest.main()
