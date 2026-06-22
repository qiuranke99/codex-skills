#!/usr/bin/env python3
"""Contract tests for skill-level creative direction requirements."""

from __future__ import annotations

import json
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]


def read_text(rel: str) -> str:
    return (SKILL_DIR / rel).read_text(encoding="utf-8")


def packaged_paths() -> list[str]:
    manifest = json.loads(read_text("references/source_manifest.json"))
    return [entry["path"] for entry in manifest["canonical_packaged_references"]]


class SkillContractQualityTests(unittest.TestCase):
    def test_skill_removes_blue_gray_storyboard_style_dependency(self) -> None:
        retired_paths = [
            "references/blue_gray_previs_style_bible.md",
            "assets/blue_gray_previs_reference.jpeg",
        ]
        for rel in retired_paths:
            self.assertFalse((SKILL_DIR / rel).exists(), f"retired style dependency still exists: {rel}")
            self.assertNotIn(rel, packaged_paths())

        forbidden_tokens = [
            "blue" + "-gray",
            "blue" + "_gray",
            "blue gray",
            "blue" + "-gray previs",
            "blue" + "_gray_previs",
            "blue" + "_gray_previs_style_bible",
            "blue" + "_gray_previs_reference",
            "very light " + "blue" + "-gray storyboard wash",
            "\u84dd\u7070",
        ]

        searchable_paths = [
            path
            for path in packaged_paths()
            if path != "tests/test_skill_contract_quality.py"
            and not path.lower().endswith((".jpeg", ".jpg", ".png", ".webp"))
        ]
        searchable_paths.extend(["AGENTS.md", "agents/openai.yaml"])

        violations: list[str] = []
        for rel in sorted(set(searchable_paths)):
            path = SKILL_DIR / rel
            if not path.exists():
                continue
            lowered = path.read_text(encoding="utf-8").lower()
            for token in forbidden_tokens:
                if token.lower() in lowered:
                    violations.append(f"{rel}: contains {token!r}")

        self.assertEqual([], violations)

    def test_package_verifier_enforces_the_new_contract(self) -> None:
        verifier = read_text("scripts/verify_skill_package.py")
        self.assertNotIn("blue" + "_gray_previs_style_bible", verifier)
        self.assertNotIn("blue" + "_gray_previs_reference", verifier)
        self.assertIn("tests/test_skill_contract_quality.py", verifier)

    def test_role_agents_encode_premium_category_expertise(self) -> None:
        combined = "\n".join(
            [
                read_text("SKILL.md"),
                read_text("AGENTS.md"),
                read_text("references/workflow_contract.md"),
                read_text("references/director_kernel.md"),
                read_text("references/world_class_tvc_principles.md"),
                read_text("references/shot_spec_template.md"),
            ]
        )

        required_phrases = [
            "premium beauty",
            "premium skincare",
            "fast-moving consumer goods",
            "luxury goods",
            "category truth",
            "purchase ritual",
            "shelf memory",
            "ritual proof",
            "edit bridge",
            "transition grammar",
            "lens progression",
            "shot-to-shot causality",
            "reference-to-world transformation",
            "invented scene architecture",
            "prop logic",
        ]
        missing = [phrase for phrase in required_phrases if phrase not in combined]
        self.assertEqual([], missing)

    def test_director_and_art_director_have_stronger_failure_ownership(self) -> None:
        agents = read_text("AGENTS.md")

        director_requirements = [
            "lens progression",
            "transition grammar",
            "edit bridge",
            "motivated camera path",
            "shot-to-shot causality",
            "coverage strategy",
        ]
        art_director_requirements = [
            "reference-to-world transformation",
            "invented scene architecture",
            "prop logic",
            "material system",
            "category-coded restraint",
            "set-piece invention",
        ]

        for phrase in director_requirements:
            self.assertIn(phrase, agents)
        for phrase in art_director_requirements:
            self.assertIn(phrase, agents)


if __name__ == "__main__":
    raise SystemExit(unittest.main())
