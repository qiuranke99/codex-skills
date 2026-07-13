#!/usr/bin/env python3
from __future__ import annotations

import base64
import hashlib
import json
import subprocess
import sys
import tempfile
from copy import deepcopy
from pathlib import Path


HERE = Path(__file__).resolve().parent
INIT = HERE / "init_asset_package.py"
VALIDATE = HERE / "validate_asset_package.py"
MANIFEST = "asset_package_manifest.json"
SPECIFICATION = "01_Product_Identity_Specification.md"
PROMPTS = "08_4K_Upscale_Prompts.md"

PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Y9Z4ioAAAAASUVORK5CYII="
)
ASSET_NAMES = {
    "geometry_lock": "02_Geometry_Lock_Board/geometry_lock_board.png",
    "material_surface_lock": "03_Material_Surface_Lock/material_surface_lock_board.png",
    "component_detail_lock": "04_Component_Detail_Lock/component_detail_lock_board.png",
    "state_transition_lock": "05_State_Transition_Lock/state_transition_lock_board.png",
    "marking_identity_lock": "06_Marking_Identity_Lock/marking_identity_lock_board.png",
    "final_product_identity_lock_board": "07_Final_Product_Identity_Lock_Board/final_product_identity_lock_board.png",
}


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, text=True, capture_output=True, encoding="utf-8")


def read_manifest(package: Path) -> dict:
    return json.loads((package / MANIFEST).read_text(encoding="utf-8"))


def write_manifest(package: Path, manifest: dict) -> None:
    (package / MANIFEST).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )


def initialize(parent: Path, name: str) -> Path:
    package = parent / name / "Complex_Product_Identity_Asset_Package"
    result = run([sys.executable, str(INIT), "--output", str(package), "--asset-id", name.replace("_", "-")])
    if result.returncode != 0:
        raise AssertionError(f"initializer failed: {result.stderr}")
    manifest = read_manifest(package)
    specification = (package / SPECIFICATION).read_text(encoding="utf-8")
    manifest["identity_specification_sha256"] = sha(specification)
    manifest["source_bundle_sha256"] = sha(f"source-bundle:{name}")
    write_manifest(package, manifest)
    return package


def approve_record(package: Path, record: dict, board_id: str) -> None:
    asset_file = ASSET_NAMES[board_id]
    asset_path = package / asset_file
    asset_path.write_bytes(PNG_1X1)
    record.update(
        {
            "source_gate": "approved",
            "source_gate_reasons": [],
            "evidence_ids": ["S01", "S02"],
            "status": "approved",
            "attempt_count": 1,
            "terminal_generation_call": "executed",
            "asset_file": asset_file,
            "actual_dimensions": {"width": 1672, "height": 941},
            "generation_prompt_sha256": sha(f"private-prompt:{board_id}"),
            "native_4k_claimed": False,
            "native_4k_evidence": None,
            "qa": {
                "geometry_consistency": "pass",
                "material_consistency": "pass",
                "identity_consistency": "pass",
                "failure_flags": [],
            },
        }
    )


def prompt_mapping(asset_file: str) -> dict:
    return {
        "asset_file": asset_file,
        "section_anchor": f"Asset: {asset_file}",
        "preserves": ["geometry", "part_count", "proportions", "markings", "materials"],
        "allowed_changes": ["resolution", "edge_definition", "realistic_microtexture"],
        "redesign_forbidden": True,
    }


def prompt_section(asset_file: str) -> str:
    return f"""## Asset: {asset_file}

Preserve original product geometry. Preserve part count. Preserve proportions.
Preserve any source-supported logo and markings exactly; do not invent them if absent.
Preserve materials and colors. Enhance only clarity and realistic micro-texture.
Do not redesign the product.
"""


def write_prompt_package(package: Path, approved_assets: list[str]) -> None:
    body = "# 4K Upscale Prompts\n\n" + "\n".join(prompt_section(asset) for asset in approved_assets)
    (package / PROMPTS).write_text(body, encoding="utf-8", newline="\n")


def make_full(parent: Path, name: str = "full-valid") -> Path:
    package = initialize(parent, name)
    manifest = read_manifest(package)
    approved_assets: list[str] = []
    source_board_ids: list[str] = []
    for record in manifest["boards"]:
        record["relevance"] = "required"
        approve_record(package, record, record["board_id"])
        approved_assets.append(record["asset_file"])
        source_board_ids.append(record["board_id"])
    final = manifest["final_board"]
    approve_record(package, final, final["board_id"])
    final["source_board_ids"] = source_board_ids
    approved_assets.append(final["asset_file"])
    manifest["package_status"] = "complete"
    manifest["four_k_prompts"] = [prompt_mapping(asset) for asset in approved_assets]
    manifest["approved_asset_count"] = len(approved_assets)
    manifest["four_k_mapping_count"] = len(approved_assets)
    write_prompt_package(package, approved_assets)
    write_manifest(package, manifest)
    return package


def make_partial(parent: Path, name: str = "partial-valid") -> Path:
    package = initialize(parent, name)
    manifest = read_manifest(package)
    geometry = next(record for record in manifest["boards"] if record["board_id"] == "geometry_lock")
    approve_record(package, geometry, "geometry_lock")
    for record in manifest["boards"]:
        if record is geometry:
            continue
        record.update(
            {
                "relevance": "conditional",
                "source_gate": "blocked",
                "source_gate_reasons": ["insufficient evidence"],
                "status": "blocked",
            }
        )
    manifest["final_board"]["status"] = "blocked"
    manifest["final_board"]["source_gate_reasons"] = ["required board blocked"]
    manifest["package_status"] = "partial_approved"
    asset = geometry["asset_file"]
    manifest["four_k_prompts"] = [prompt_mapping(asset)]
    manifest["approved_asset_count"] = 1
    manifest["four_k_mapping_count"] = 1
    write_prompt_package(package, [asset])
    write_manifest(package, manifest)
    return package


def make_blocked(parent: Path) -> Path:
    package = initialize(parent, "blocked-valid")
    manifest = read_manifest(package)
    for record in manifest["boards"]:
        if record["board_id"] == "geometry_lock":
            record.update(
                {
                    "relevance": "required",
                    "source_gate": "blocked",
                    "source_gate_reasons": ["rear and underside unknown"],
                    "status": "blocked",
                }
            )
        else:
            record.update(
                {
                    "relevance": "not_applicable",
                    "source_gate": "not_applicable",
                    "source_gate_reasons": ["not evaluated after geometry block"],
                    "status": "not_applicable",
                }
            )
    manifest["package_status"] = "blocked_source_insufficient"
    write_manifest(package, manifest)
    return package


def expect_valid(package: Path, label: str) -> None:
    result = run([sys.executable, str(VALIDATE), str(package)])
    if result.returncode != 0:
        raise AssertionError(f"{label} should pass:\n{result.stdout}\n{result.stderr}")
    print(f"PASS valid: {label}")


def expect_invalid(package: Path, label: str, fragment: str) -> None:
    result = run([sys.executable, str(VALIDATE), str(package)])
    combined = (result.stdout + result.stderr).casefold()
    if result.returncode == 0 or fragment.casefold() not in combined:
        raise AssertionError(
            f"{label} should fail with {fragment!r}:\nreturn={result.returncode}\n{combined}"
        )
    print(f"PASS invalid: {label}")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="complex-product-contract-") as temp:
        root = Path(temp)
        expect_valid(make_full(root), "complete package")
        expect_valid(make_partial(root), "partial approved package")
        expect_valid(make_blocked(root), "blocked source-insufficient package")

        missing_mapping = make_full(root, "missing-mapping")
        manifest = read_manifest(missing_mapping)
        manifest["four_k_prompts"].pop()
        manifest["four_k_mapping_count"] -= 1
        write_manifest(missing_mapping, manifest)
        expect_invalid(missing_mapping, "complete missing 4K mapping", "one-to-one")

        awaiting = make_full(root, "awaiting-continuation")
        manifest = read_manifest(awaiting)
        component = next(record for record in manifest["boards"] if record["board_id"] == "component_detail_lock")
        component["relevance"] = "conditional"
        component["status"] = "awaiting_post_generation_continuation"
        manifest["final_board"]["source_board_ids"].remove("component_detail_lock")
        manifest["four_k_prompts"] = [
            mapping for mapping in manifest["four_k_prompts"] if mapping["asset_file"] != component["asset_file"]
        ]
        remaining_assets = [mapping["asset_file"] for mapping in manifest["four_k_prompts"]]
        manifest["approved_asset_count"] = len(remaining_assets)
        manifest["four_k_mapping_count"] = len(remaining_assets)
        write_prompt_package(awaiting, remaining_assets)
        write_manifest(awaiting, manifest)
        expect_invalid(awaiting, "complete awaiting continuation", "unfinished generation states")

        unsupported_state = make_full(root, "unsupported-state")
        manifest = read_manifest(unsupported_state)
        state = next(record for record in manifest["boards"] if record["board_id"] == "state_transition_lock")
        state["source_gate"] = "blocked"
        state["source_gate_reasons"] = ["state inferred only"]
        write_manifest(unsupported_state, manifest)
        expect_invalid(unsupported_state, "approved state with blocked source gate", "requires source_gate: approved")

        false_4k = make_partial(root, "false-native-4k")
        manifest = read_manifest(false_4k)
        geometry = next(record for record in manifest["boards"] if record["board_id"] == "geometry_lock")
        geometry["native_4k_claimed"] = True
        geometry["native_4k_evidence"] = None
        write_manifest(false_4k, manifest)
        expect_invalid(false_4k, "native 4K claim on Codex asset", "must remain false for codex package assets")

    print("contract tests: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
