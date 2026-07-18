#!/usr/bin/env python3
"""Coverage-derived material source-contract v2 tests."""

from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from material_contract import (
    MaterialContractError,
    canonical_json_bytes,
    load_source_contract,
    normalize_source_contract_draft,
    pretty_json_bytes,
    render_material_prompt_block,
    render_reconstruction_fact_statement,
    sha256_bytes,
    source_contract_core,
    validate_source_contract_research_binding,
)
from material_research import freeze_research_document
from test_material_research import build_draft as build_research_draft


HASH_A = "a" * 64
HASH_B = "b" * 64


def manifest(*aliases: str) -> dict[str, object]:
    return {
        "aliases": list(aliases),
        "sha256": HASH_A,
        "ordered_bundle_sha256": HASH_B,
    }


def source(
    alias: str,
    *,
    subject_match_class: str = "user_source_exact_visible",
    observed_surfaces: list[str] | None = None,
    view_bins: list[str] | None = None,
) -> dict[str, object]:
    return {
        "alias": alias,
        "authority": (
            "authoritative_source"
            if subject_match_class == "user_source_exact_visible"
            else "supporting_source"
        ),
        "subject_match_class": subject_match_class,
        "observed_surfaces": observed_surfaces or ["front"],
        "view_bins": view_bins or ["front"],
        "generation_reference_use_allowed": True,
        "research_claim_ids": [],
        "allowed_uses": [
            "identity",
            "silhouette",
            "proportions",
            "color",
            "material",
            "topology",
            "structure",
            "label_layout",
            "state",
            "panel_composition",
        ],
        "exclusions": [],
    }


def fact(fact_id: str, statement: str, *, alias: str = "product_front") -> dict[str, object]:
    return {
        "fact_id": fact_id,
        "statement": statement,
        "source_aliases": [alias],
        "research_claim_ids": [],
    }


def panel(
    panel_id: str,
    role: str,
    invariant_id: str,
    *,
    aliases: list[str] | None = None,
    view_authority: str = "direct_source",
    target_surfaces: list[str] | None = None,
    research_claim_ids: list[str] | None = None,
) -> dict[str, object]:
    if view_authority == "same_family_reconstruction":
        evidence_job = "same_family_geometry_reconstruction"
    elif view_authority == "packaging_archetype_reconstruction":
        evidence_job = "packaging_archetype_structure_reconstruction"
    elif view_authority == "exact_variant_hidden_surface":
        evidence_job = "exact_hidden_surface"
    else:
        evidence_job = {
            "primary_anchor": "front_identity_anchor",
            "material_response": "front_material_response",
            "critical_structure": "front_visible_structure",
            "label_micro": "front_label_micro",
            "multi_angle": "source_observed_multi_angle",
            "state_window": "state_evidence_window",
        }[role]
    return {
        "panel_id": panel_id,
        "role": role,
        "evidence_job": evidence_job,
        "source_aliases": aliases or ["product_front"],
        "invariant_ids": [invariant_id],
        "view_authority": view_authority,
        "target_surfaces": target_surfaces or ["front"],
        "research_claim_ids": research_claim_ids or [],
        "required_for_acceptance": True,
    }


def clear_front_draft() -> dict[str, object]:
    return {
        "schema_version": "material_source_contract_draft.v2",
        "asset_id": "gliss-lumiere-aurora-100ml",
        "source_coverage_profile": "clear_front_only",
        "research_path": "C:\\material-research.json",
        "research_sha256": HASH_A,
        "source_authority": [source("product_front")],
        "fact_registry": {
            "verified": [
                fact("identity-visible", "Visible target identity and silhouette are authoritative."),
                fact("material-visible", "Visible front optical response is authoritative."),
                fact("structure-visible", "Visible front structure is authoritative."),
                fact("label-visible", "Visible front label layout is authoritative."),
            ],
            "inferred": [],
            "needs_source": [
                {
                    "fact_id": "rear-copy-unknown",
                    "statement": "Rear copy is unresolved and must not be invented.",
                    "source_aliases": [],
                    "research_claim_ids": [],
                }
            ],
        },
        "critical_invariants": [
            {
                "invariant_id": "inv-identity",
                "category": "identity",
                "fact_id": "identity-visible",
                "required_for_acceptance": True,
            },
            {
                "invariant_id": "inv-material",
                "category": "material",
                "fact_id": "material-visible",
                "required_for_acceptance": True,
            },
            {
                "invariant_id": "inv-structure",
                "category": "structure",
                "fact_id": "structure-visible",
                "required_for_acceptance": True,
            },
            {
                "invariant_id": "inv-label",
                "category": "label_layout",
                "fact_id": "label-visible",
                "required_for_acceptance": True,
            },
        ],
        "panel_plan": [
            panel("front-anchor", "primary_anchor", "inv-identity"),
            panel("front-material", "material_response", "inv-material"),
            panel("front-structure", "critical_structure", "inv-structure"),
            panel("front-label", "label_micro", "inv-label"),
        ],
    }


def write_research(run_dir: Path, draft: dict[str, object]) -> tuple[Path, str]:
    frozen = freeze_research_document(draft, draft_dir=run_dir)
    path = run_dir / "sources" / "material-research.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(frozen, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    path.write_bytes(payload)
    return path, hashlib.sha256(payload).hexdigest()


def reconstruction_statement(research_path: Path, *claim_ids: str) -> str:
    research = json.loads(research_path.read_text(encoding="utf-8"))
    by_id = {claim["claim_id"]: claim for claim in research["structure_claims"]}
    return render_reconstruction_fact_statement([by_id[claim_id] for claim_id in claim_ids])


class MaterialCoverageContractTests(unittest.TestCase):
    def assert_code(self, expected: str, draft: dict[str, object], record: dict[str, object]) -> None:
        with self.assertRaises(MaterialContractError) as caught:
            normalize_source_contract_draft(draft, record)
        self.assertEqual(expected, caught.exception.code)

    def test_clear_front_only_truthful_four_panel_contract_has_zero_multi_angle(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            run_dir = Path(temp).resolve()
            research_path, research_sha = write_research(run_dir, build_research_draft(run_dir))
            draft = clear_front_draft()
            draft["research_path"] = str(research_path)
            draft["research_sha256"] = research_sha
            normalized = normalize_source_contract_draft(draft, manifest("product_front"))
            validate_source_contract_research_binding(normalized, run_dir)
            self.assertEqual("material_source_contract.v2", normalized["schema_version"])
            self.assertEqual("clear_front_only", normalized["source_coverage_profile"])
            self.assertEqual(4, len(normalized["panel_plan"]))
            self.assertFalse(any(p["role"] == "multi_angle" for p in normalized["panel_plan"]))
            first_hash = sha256_bytes(canonical_json_bytes(source_contract_core(normalized)))
            second = normalize_source_contract_draft(copy.deepcopy(draft), manifest("product_front"))
            self.assertEqual(first_hash, sha256_bytes(canonical_json_bytes(source_contract_core(second))))

    def test_v2_requires_raw_file_sha_bound_research_artifact(self) -> None:
        draft = clear_front_draft()
        draft["research_path"] = ""
        draft["research_sha256"] = ""
        self.assert_code(
            "blocked_material_source_contract_invalid", draft, manifest("product_front")
        )

    def test_provider_manifest_must_equal_rights_selected_research_captures(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            run_dir = Path(temp).resolve()
            research_draft = build_research_draft(run_dir)
            research_draft["evidence"][0]["reference_alias"] = "product_front"
            research_path, research_sha = write_research(run_dir, research_draft)
            draft = clear_front_draft()
            draft["research_path"] = str(research_path)
            draft["research_sha256"] = research_sha
            normalized = normalize_source_contract_draft(draft, manifest("product_front"))
            selected_capture_sha = json.loads(research_path.read_text(encoding="utf-8"))[
                "evidence"
            ][0]["capture"]["sha256"]
            matching_manifest = {
                "entries": [
                    {"alias": "product_front", "sha256": selected_capture_sha}
                ]
            }
            self.assertIsNotNone(
                validate_source_contract_research_binding(
                    normalized, run_dir, matching_manifest
                )
            )
            mismatched_manifest = {
                "entries": [{"alias": "product_front", "sha256": "0" * 64}]
            }
            with self.assertRaises(MaterialContractError) as caught:
                validate_source_contract_research_binding(
                    normalized, run_dir, mismatched_manifest
                )
            self.assertEqual("blocked_reference_generation_rights", caught.exception.code)

    def test_v2_contract_and_prompt_round_trip_preserves_raw_research_file_hash(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            run_dir = Path(temp).resolve()
            research_path, research_sha = write_research(run_dir, build_research_draft(run_dir))
            draft = clear_front_draft()
            draft["research_path"] = str(research_path)
            draft["research_sha256"] = research_sha
            record = manifest("product_front")
            normalized = normalize_source_contract_draft(draft, record)
            normalized["reference_manifest_path"] = str(
                run_dir / "sources" / "reference-manifest.json"
            )
            core = source_contract_core(normalized)
            core_sha = sha256_bytes(canonical_json_bytes(core))
            block_path = run_dir / "sources" / "material-prompt-block.md"
            block_bytes = render_material_prompt_block(core, core_sha)
            block_path.write_bytes(block_bytes)
            contract = {
                **core,
                "contract_core_sha256": core_sha,
                "prompt_block_path": str(block_path),
                "prompt_block_sha256": sha256_bytes(block_bytes),
                "immutability_contract": "create_only_idempotent;rehash_at_every_transition",
            }
            contract_path = run_dir / "sources" / "material-source-contract.json"
            contract_path.write_bytes(pretty_json_bytes(contract))
            loaded = load_source_contract(contract_path, run_dir, record)
            self.assertEqual(research_sha, loaded["core"]["research_sha256"])
            self.assertEqual(research_sha, sha256_bytes(research_path.read_bytes()))

    def test_front_source_cannot_launder_rear_or_side_as_exact(self) -> None:
        for target in ("rear", "left_side"):
            with self.subTest(target=target):
                draft = clear_front_draft()
                draft["panel_plan"].append(  # type: ignore[index,union-attr]
                    panel(
                        f"fake-{target}",
                        "multi_angle",
                        "inv-identity",
                        view_authority="direct_source",
                        target_surfaces=[target],
                    )
                )
                self.assert_code(
                    "blocked_panel_view_authority_laundering",
                    draft,
                    manifest("product_front"),
                )

    def test_same_family_reconstruction_uses_exact_target_ref_plus_hash_bound_claim(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            run_dir = Path(temp).resolve()
            research_path, research_sha = write_research(run_dir, build_research_draft(run_dir))
            draft = clear_front_draft()
            draft["research_path"] = str(research_path)
            draft["research_sha256"] = research_sha
            draft["fact_registry"]["inferred"].append(  # type: ignore[index,union-attr]
                {
                    "fact_id": "family-depth-reconstruction",
                    "statement": reconstruction_statement(
                        research_path, "structure-family-depth"
                    ),
                    "source_aliases": ["product_front"],
                    "research_claim_ids": ["structure-family-depth"],
                }
            )
            draft["panel_plan"].append(  # type: ignore[index,union-attr]
                panel(
                    "left-reconstruction",
                    "multi_angle",
                    "inv-identity",
                    view_authority="same_family_reconstruction",
                    target_surfaces=["left_side"],
                    research_claim_ids=["structure-family-depth"],
                )
            )
            normalized = normalize_source_contract_draft(draft, manifest("product_front"))
            normalized["reference_manifest_path"] = str(run_dir / "sources" / "reference-manifest.json")
            result = validate_source_contract_research_binding(normalized, run_dir)
            self.assertIsNotNone(result)
            self.assertEqual(["product_front"], [s["alias"] for s in normalized["source_authority"]])
            self.assertEqual(
                "same_family_reconstruction", normalized["panel_plan"][-1]["view_authority"]
            )

    def test_archetype_pump_claim_cannot_upgrade_to_verified_exact_fact(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            run_dir = Path(temp).resolve()
            research_path, research_sha = write_research(run_dir, build_research_draft(run_dir))
            draft = clear_front_draft()
            draft["research_path"] = str(research_path)
            draft["research_sha256"] = research_sha
            pump_fact = {
                "fact_id": "pump-stack-reconstruction",
                "statement": reconstruction_statement(research_path, "structure-pump-stack"),
                "source_aliases": ["product_front"],
                "research_claim_ids": ["structure-pump-stack"],
            }
            draft["fact_registry"]["inferred"].append(pump_fact)  # type: ignore[index,union-attr]
            draft["panel_plan"].append(  # type: ignore[index,union-attr]
                panel(
                    "open-cap-reconstruction",
                    "critical_structure",
                    "inv-structure",
                    view_authority="packaging_archetype_reconstruction",
                    target_surfaces=["open_cap"],
                    research_claim_ids=["structure-pump-stack"],
                )
            )
            normalized = normalize_source_contract_draft(draft, manifest("product_front"))
            validate_source_contract_research_binding(normalized, run_dir)

            malicious = copy.deepcopy(draft)
            malicious["fact_registry"]["inferred"][-1]["statement"] = (  # type: ignore[index]
                "Render the exact rear copy, exact pump material, and exact hidden geometry."
            )
            normalized_malicious = normalize_source_contract_draft(
                malicious, manifest("product_front")
            )
            with self.assertRaises(MaterialContractError) as caught:
                validate_source_contract_research_binding(normalized_malicious, run_dir)
            self.assertEqual(
                "blocked_reconstruction_statement_invalid", caught.exception.code
            )

            poisoned = copy.deepcopy(draft)
            moved = poisoned["fact_registry"]["inferred"].pop()  # type: ignore[index,union-attr]
            poisoned["fact_registry"]["verified"].append(moved)  # type: ignore[index,union-attr]
            normalized_poisoned = normalize_source_contract_draft(
                poisoned, manifest("product_front")
            )
            with self.assertRaises(MaterialContractError) as caught:
                validate_source_contract_research_binding(normalized_poisoned, run_dir)
            self.assertEqual("blocked_research_fact_authority", caught.exception.code)

    def test_exact_variant_rear_capture_allows_exact_hidden_panel(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            run_dir = Path(temp).resolve()
            research_draft = build_research_draft(run_dir)
            exact_evidence = next(
                item for item in research_draft["evidence"] if item["evidence_id"] == "ev-exact-front"  # type: ignore[index]
            )
            exact_evidence["selected_generation_reference"] = True
            exact_evidence["reference_alias"] = "exact-rear"
            exact_evidence["rights_status"] = "licensed"
            exact_evidence["observations"].append(  # type: ignore[index,union-attr]
                {
                    "observation_id": "obs-exact-rear",
                    "surface": "rear",
                    "claim_kind": "surface_geometry",
                    "support_mode": "direct_visual",
                    "statement": "The exact-variant capture directly shows the rear surface.",
                    "authority": "direct_exact",
                    "prompt_eligible": False,
                }
            )
            research_draft["surface_coverage"].append(  # type: ignore[index,union-attr]
                {
                    "coverage_id": "coverage-rear-exact",
                    "surface": "rear",
                    "authority": "exact_variant_hidden_surface",
                    "usable_for": "exact_render",
                    "evidence_ids": ["ev-exact-front"],
                    "structure_claim_ids": [],
                }
            )
            research_path, research_sha = write_research(run_dir, research_draft)
            draft = clear_front_draft()
            draft["research_path"] = str(research_path)
            draft["research_sha256"] = research_sha
            draft["source_coverage_profile"] = "partial_multiview"
            draft["source_authority"].append(  # type: ignore[union-attr]
                source(
                    "exact_rear",
                    subject_match_class="exact_variant",
                    observed_surfaces=["rear"],
                    view_bins=["rear"],
                )
            )
            draft["panel_plan"].append(  # type: ignore[index,union-attr]
                panel(
                    "rear-exact",
                    "multi_angle",
                    "inv-identity",
                    aliases=["product_front", "exact_rear"],
                    view_authority="exact_variant_hidden_surface",
                    target_surfaces=["rear"],
                )
            )
            normalized = normalize_source_contract_draft(
                draft, manifest("product_front", "exact_rear")
            )
            validate_source_contract_research_binding(normalized, run_dir)
            self.assertEqual("partial_multiview", normalized["source_coverage_profile"])


if __name__ == "__main__":
    unittest.main()
