#!/usr/bin/env python3
from __future__ import annotations

import base64
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path


HERE = Path(__file__).resolve().parent
INIT = HERE / "init_asset_package.py"
VALIDATE = HERE / "validate_asset_package.py"
MANIFEST = "asset_package_manifest.json"
SPECIFICATION = "01_Product_Identity_Specification.md"
REPORT = "02_Geometry_Camera_Coverage/camera_coverage_report.md"
PROMPTS = "08_4K_Upscale_Prompts.md"

PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Y9Z4ioAAAAASUVORK5CYII="
)
BOARD_ASSET_NAMES = {
    "material_surface_lock": "03_Material_Surface_Lock/material_surface_lock_board.png",
    "component_detail_lock": "04_Component_Detail_Lock/component_detail_lock_board.png",
    "state_transition_lock": "05_State_Transition_Lock/state_transition_lock_board.png",
    "marking_identity_lock": "06_Marking_Identity_Lock/marking_identity_lock_board.png",
}


def assert_standalone_skill_contract() -> None:
    skill_dir = HERE.parent
    required = (
        "SKILL.md",
        "agents/openai.yaml",
        "references/product-identity-contract.md",
        "references/generation-runtime-and-qa.md",
        "references/package-contract.md",
        "references/test-cases.md",
        "standalone-validation.json",
        "scripts/init_asset_package.py",
        "scripts/validate_asset_package.py",
    )
    for relative in required:
        if not (skill_dir / relative).is_file():
            raise AssertionError(f"standalone package is missing {relative}")

    forbidden_text = (
        "HIGH_CONTROL_" + "RELEASE_GATE_V2",
        "high-control-" + "ai-tvc",
        "release-" + "control.ps1",
        "release-" + "control.sh",
        "ready_" + "latest=true",
    )
    text_suffixes = {".md", ".py", ".yaml", ".json", ".txt"}
    for path in skill_dir.rglob("*"):
        if not path.is_file() or path.suffix.casefold() not in text_suffixes:
            continue
        text = path.read_text(encoding="utf-8")
        for marker in forbidden_text:
            if marker in text:
                raise AssertionError(f"standalone package retains external runtime marker {marker!r} in {path.relative_to(skill_dir)}")
        if path.suffix.casefold() == ".py":
            if ("sys.path." + "insert") in text or (".parents[" + "2]") in text:
                raise AssertionError(f"standalone package retains a cross-package Python loader in {path.relative_to(skill_dir)}")

    skill = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    metadata = (skill_dir / "agents/openai.yaml").read_text(encoding="utf-8")
    if "## Standalone Runtime Contract" not in skill:
        raise AssertionError("SKILL.md is missing the standalone runtime contract")
    if "allow_implicit_invocation: true" not in metadata:
        raise AssertionError("complex-product invocation metadata drifted")


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_text(text: str) -> str:
    return sha_bytes(text.encode("utf-8"))


def camera_plan_sha256(geometry: dict) -> str:
    payload = {
        "minimum_video_ready_camera_count": geometry["minimum_video_ready_camera_count"],
        "target_camera_ids": geometry["target_camera_ids"],
        "cameras": [
            {
                "camera_id": item["camera_id"],
                "role": item["role"],
                "pose_bin": item["pose_bin"],
                "coverage_sectors": item["coverage_sectors"],
            }
            for item in geometry["camera_assets"]
        ],
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha_bytes(encoded)


def unique_png(label: str) -> bytes:
    return PNG_1X1 + label.encode("utf-8")


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
    manifest["identity_specification_sha256"] = sha_text(specification)
    manifest["source_bundle_sha256"] = sha_text(f"source-bundle:{name}")
    (package / REPORT).write_text(
        "# Camera Coverage Report\n\nStatus: frozen\n\n## Accepted Independent Cameras\n\n## Blocked Cameras And Exact Evidence Requests\n\n## Coverage Metrics\n\n## Downstream Upload Recommendation\n",
        encoding="utf-8",
        newline="\n",
    )
    write_manifest(package, manifest)
    return package


def pass_camera_qa() -> dict:
    return {
        "subject_match": "pass",
        "complete_product": "pass",
        "pose_match": "pass",
        "critical_node_consistency": "pass",
        "cross_camera_consistency": "pass",
        "text_pollution": "pass",
        "failure_flags": [],
    }


def approve_camera(package: Path, record: dict, *, mode: str = "verified_source_render") -> None:
    asset_file = f"02_Geometry_Camera_Coverage/camera_assets/{record['camera_id'].casefold()}.png"
    data = unique_png(record["camera_id"])
    (package / asset_file).write_bytes(data)
    record.update(
        {
            "source_gate": "approved",
            "source_gate_reasons": [],
            "source_ids": ["S01", "S02"],
            "critical_node_ids": ["NODE_FRAME", "NODE_WHEEL_AXLE"],
            "evidence_mode": mode,
            "identity_authority": "hard" if mode in {"source_copy", "verified_source_render"} else "auxiliary",
            "status": "approved",
            "attempt_count": 1,
            "terminal_generation_call": "not_applicable" if mode in {"source_copy", "verified_source_render"} else "executed",
            "asset_file": asset_file,
            "asset_sha256": sha_bytes(data),
            "source_asset_sha256": sha_bytes(data) if mode == "source_copy" else sha_text(f"source:{record['camera_id']}"),
            "provenance_sha256": sha_text(f"provenance:{record['camera_id']}") if mode == "verified_source_render" else None,
            "actual_dimensions": {"width": 1, "height": 1},
            "generation_prompt_sha256": sha_text(f"private-prompt:{record['camera_id']}") if mode in {"source_aligned_generation", "bounded_reconstruction"} else None,
            "qa": pass_camera_qa(),
        }
    )


def block_camera(record: dict, reason: str = "specific rear or underside evidence is missing") -> None:
    record.update(
        {
            "source_gate": "blocked",
            "source_gate_reasons": [reason],
            "source_ids": [],
            "critical_node_ids": [],
            "evidence_mode": "blocked",
            "identity_authority": "none",
            "status": "blocked",
        }
    )


def update_coverage_metrics(manifest: dict) -> None:
    geometry = manifest["geometry_coverage"]
    approved = [item for item in geometry["camera_assets"] if item["status"] == "approved"]
    hard = [item for item in approved if item["identity_authority"] == "hard"]
    poses = {
        (item["pose_bin"]["azimuth"], item["pose_bin"]["elevation"], item["pose_bin"]["shot_size"])
        for item in approved
    }
    sectors = sorted({sector for item in approved for sector in item["coverage_sectors"]})
    elevations = sorted({item["pose_bin"]["elevation"] for item in approved})
    hashes = [item["asset_sha256"] for item in approved]
    redundancy = (len(approved) - len(poses)) + (len(hashes) - len(set(hashes)))
    minimum = geometry["minimum_video_ready_camera_count"]
    video_ready = (
        len(hard) >= minimum
        and len(poses) >= minimum
        and {"front", "rear"} <= set(sectors)
        and bool({"left", "right", "side"} & set(sectors))
        and redundancy == 0
    )
    full = video_ready and len(approved) == len(geometry["target_camera_ids"]) and len(hard) == len(approved)
    geometry["coverage_metrics"] = {
        "approved_camera_count": len(approved),
        "hard_authority_camera_count": len(hard),
        "unique_pose_bin_count": len(poses),
        "covered_sectors": sectors,
        "elevation_bands": elevations,
        "redundancy_count": redundancy,
        "coverage_tier": "full" if full else "multi_camera" if video_ready else "source_aligned" if approved else "none",
    }


def approve_board(package: Path, record: dict) -> None:
    asset_file = BOARD_ASSET_NAMES[record["board_id"]]
    data = unique_png(record["board_id"])
    (package / asset_file).write_bytes(data)
    record.update(
        {
            "source_gate": "approved",
            "source_gate_reasons": [],
            "evidence_ids": ["S01", "S02"],
            "status": "approved",
            "attempt_count": 1,
            "terminal_generation_call": "executed",
            "asset_file": asset_file,
            "asset_sha256": sha_bytes(data),
            "actual_dimensions": {"width": 1, "height": 1},
            "generation_prompt_sha256": sha_text(f"private-prompt:{record['board_id']}"),
            "native_4k_claimed": False,
            "native_4k_evidence": None,
            "qa": {
                "geometry_consistency": "pass",
                "material_consistency": "pass",
                "identity_consistency": "pass",
                "subject_match": "pass",
                "text_pollution": "pass",
                "failure_flags": [],
            },
        }
    )


def prompt_mapping(asset_file: str) -> dict:
    return {
        "asset_file": asset_file,
        "section_anchor": f"Asset: {asset_file}",
        "preserves": ["geometry", "part_count", "proportions", "markings", "materials", "camera_pose", "critical_nodes"],
        "allowed_changes": ["resolution", "edge_definition", "realistic_microtexture"],
        "redesign_forbidden": True,
    }


def prompt_section(asset_file: str) -> str:
    return f"""## Asset: {asset_file}

Preserve original product geometry. Preserve part count. Preserve proportions.
Preserve the accepted camera pose. Preserve all critical nodes and their connections.
Preserve any source-supported logo and markings exactly; do not invent them if absent.
Preserve materials and colors. Enhance only clarity and realistic micro-texture.
Do not redesign the product.
"""


def write_prompt_package(package: Path, approved_assets: list[str]) -> None:
    body = "# 4K Upscale Prompts\n\n" + "\n".join(prompt_section(asset) for asset in approved_assets)
    (package / PROMPTS).write_text(body, encoding="utf-8", newline="\n")


def finalize_mappings(package: Path, manifest: dict) -> None:
    approved_assets = [
        item["asset_file"] for item in manifest["geometry_coverage"]["camera_assets"] if item["status"] == "approved"
    ]
    approved_assets.extend(
        item["asset_file"] for item in manifest["diagnostic_boards"] if item["status"] == "approved"
    )
    manifest["four_k_prompts"] = [prompt_mapping(asset) for asset in approved_assets]
    manifest["approved_asset_count"] = len(approved_assets)
    manifest["four_k_mapping_count"] = len(approved_assets)
    write_prompt_package(package, approved_assets)


def make_full(parent: Path, name: str = "full-valid") -> Path:
    package = initialize(parent, name)
    manifest = read_manifest(package)
    for camera in manifest["geometry_coverage"]["camera_assets"]:
        approve_camera(package, camera)
    update_coverage_metrics(manifest)
    manifest["geometry_coverage"]["status"] = "approved"
    for board in manifest["diagnostic_boards"]:
        board["relevance"] = "required"
        approve_board(package, board)
    selected = [item for item in manifest["geometry_coverage"]["camera_assets"] if item["status"] == "approved"][:5]
    manifest["primary_upload_bundle"] = {
        "directory": "07_Primary_Upload_Bundle",
        "status": "approved",
        "max_asset_count": 5,
        "selections": [{"asset_file": item["asset_file"], "role": item["role"], "camera_id": item["camera_id"]} for item in selected],
        "selection_reason": "Five non-redundant hard-authority cameras maximize downstream identity coverage.",
    }
    manifest["package_status"] = "complete"
    finalize_mappings(package, manifest)
    write_manifest(package, manifest)
    return package


def make_partial(parent: Path, name: str = "partial-valid") -> Path:
    package = initialize(parent, name)
    manifest = read_manifest(package)
    cameras = manifest["geometry_coverage"]["camera_assets"]
    approve_camera(package, cameras[0], mode="source_copy")
    for camera in cameras[1:]:
        block_camera(camera)
    update_coverage_metrics(manifest)
    manifest["geometry_coverage"]["status"] = "partial_approved"
    for board in manifest["diagnostic_boards"]:
        board.update(
            {
                "relevance": "conditional",
                "source_gate": "blocked",
                "source_gate_reasons": ["insufficient source evidence"],
                "status": "blocked",
            }
        )
    manifest["primary_upload_bundle"] = {
        "directory": "07_Primary_Upload_Bundle",
        "status": "approved",
        "max_asset_count": 5,
        "selections": [{"asset_file": cameras[0]["asset_file"], "role": cameras[0]["role"], "camera_id": cameras[0]["camera_id"]}],
        "selection_reason": "Only the direct source camera is hard-authority; missing cameras remain explicitly blocked.",
    }
    manifest["package_status"] = "partial_approved"
    finalize_mappings(package, manifest)
    write_manifest(package, manifest)
    return package


def make_blocked(parent: Path) -> Path:
    package = initialize(parent, "blocked-valid")
    manifest = read_manifest(package)
    for camera in manifest["geometry_coverage"]["camera_assets"]:
        block_camera(camera, "target variant or camera evidence unresolved")
    update_coverage_metrics(manifest)
    manifest["geometry_coverage"]["status"] = "blocked"
    for board in manifest["diagnostic_boards"]:
        board.update(
            {
                "relevance": "not_applicable",
                "source_gate": "not_applicable",
                "source_gate_reasons": ["not evaluated after identity block"],
                "status": "not_applicable",
            }
        )
    manifest["primary_upload_bundle"] = {
        "directory": "07_Primary_Upload_Bundle",
        "status": "blocked",
        "max_asset_count": 5,
        "selections": [],
        "selection_reason": "",
    }
    manifest["package_status"] = "blocked_source_insufficient"
    finalize_mappings(package, manifest)
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
    assert_standalone_skill_contract()
    print("PASS standalone package contract")
    with tempfile.TemporaryDirectory(prefix="complex-product-contract-v2-") as temp:
        root = Path(temp)
        expect_valid(make_full(root), "complete multi-camera package")
        expect_valid(make_partial(root), "partial one-camera source package")
        expect_valid(make_blocked(root), "blocked source-insufficient package")

        mapping_failed = make_full(root, "mapping-failed-valid")
        manifest = read_manifest(mapping_failed)
        missing_asset = manifest["four_k_prompts"].pop()["asset_file"]
        manifest["four_k_mapping_count"] -= 1
        manifest["package_status"] = "four_k_mapping_failed"
        remaining_assets = [item["asset_file"] for item in manifest["four_k_prompts"]]
        write_prompt_package(mapping_failed, remaining_assets)
        write_manifest(mapping_failed, manifest)
        expect_valid(mapping_failed, f"truthful 4K mapping failure excluding {missing_asset}")

        missing_mapping = make_full(root, "missing-mapping")
        manifest = read_manifest(missing_mapping)
        manifest["four_k_prompts"].pop()
        manifest["four_k_mapping_count"] -= 1
        write_manifest(missing_mapping, manifest)
        expect_invalid(missing_mapping, "complete missing 4K mapping", "one-to-one")

        wrong_dimensions = make_partial(root, "wrong-dimensions")
        manifest = read_manifest(wrong_dimensions)
        manifest["geometry_coverage"]["camera_assets"][0]["actual_dimensions"]["width"] = 1672
        write_manifest(wrong_dimensions, manifest)
        expect_invalid(wrong_dimensions, "declared dimensions without pixel proof", "does not match observed pixels")

        duplicate_pose = make_full(root, "duplicate-pose")
        manifest = read_manifest(duplicate_pose)
        cameras = manifest["geometry_coverage"]["camera_assets"]
        cameras[1]["pose_bin"] = dict(cameras[0]["pose_bin"])
        manifest["geometry_coverage"]["camera_plan_sha256"] = camera_plan_sha256(manifest["geometry_coverage"])
        update_coverage_metrics(manifest)
        write_manifest(duplicate_pose, manifest)
        expect_invalid(duplicate_pose, "duplicate camera pose bin", "duplicate camera bytes or pose bins")

        duplicate_bytes = make_full(root, "duplicate-bytes")
        manifest = read_manifest(duplicate_bytes)
        cameras = manifest["geometry_coverage"]["camera_assets"]
        source_path = duplicate_bytes / cameras[0]["asset_file"]
        target_path = duplicate_bytes / cameras[1]["asset_file"]
        data = source_path.read_bytes()
        target_path.write_bytes(data)
        cameras[1]["asset_sha256"] = sha_bytes(data)
        update_coverage_metrics(manifest)
        write_manifest(duplicate_bytes, manifest)
        expect_invalid(duplicate_bytes, "duplicate camera asset bytes", "duplicate camera bytes or pose bins")

        generative_hard = make_partial(root, "generative-hard-authority")
        manifest = read_manifest(generative_hard)
        camera = manifest["geometry_coverage"]["camera_assets"][0]
        camera["evidence_mode"] = "bounded_reconstruction"
        camera["identity_authority"] = "hard"
        camera["generation_prompt_sha256"] = sha_text("bounded prompt")
        camera["terminal_generation_call"] = "executed"
        write_manifest(generative_hard, manifest)
        expect_invalid(generative_hard, "bounded reconstruction promoted to truth", "must remain auxiliary")

        semantic_mismatch = make_partial(root, "semantic-mismatch")
        manifest = read_manifest(semantic_mismatch)
        camera = manifest["geometry_coverage"]["camera_assets"][0]
        camera["qa"]["subject_match"] = "fail"
        camera["qa"]["failure_flags"] = ["subject_absent", "infographic_semantics"]
        write_manifest(semantic_mismatch, manifest)
        expect_invalid(semantic_mismatch, "unrelated poster accepted as product", "subject_match must pass")

        insufficient_geometry = make_partial(root, "insufficient-geometry")
        manifest = read_manifest(insufficient_geometry)
        manifest["geometry_coverage"]["status"] = "approved"
        write_manifest(insufficient_geometry, manifest)
        expect_invalid(insufficient_geometry, "one camera claimed as multi-camera", "requires hard-authority multi-camera coverage")

        invalid_upload = make_partial(root, "invalid-upload")
        manifest = read_manifest(invalid_upload)
        manifest["primary_upload_bundle"]["selections"][0]["asset_file"] = "03_Material_Surface_Lock/not-approved.png"
        write_manifest(invalid_upload, manifest)
        expect_invalid(invalid_upload, "upload bundle selects non-approved asset", "non-approved asset")

        legacy = make_partial(root, "legacy-v1")
        manifest = read_manifest(legacy)
        manifest["schema_version"] = "complex_product_identity_asset_package.v1"
        write_manifest(legacy, manifest)
        expect_invalid(legacy, "legacy monolithic geometry manifest", "cannot prove independent camera coverage")

    print("contract tests: OK (4 valid + 9 historical/boundary failures)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
