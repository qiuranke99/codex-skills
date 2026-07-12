#!/usr/bin/env python3
"""Validate the six-skill suite and its 13-package publication surface."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable


SKILLS = (
    "ai-video-shot-script-director",
    "ai-video-global-look-lock",
    "ai-video-modular-storyboard",
    "ai-video-timed-animatic-previs-director",
    "ai-video-keyframe-continuity-pack",
    "ai-video-omni-reference-prompt-director",
)

OWNER_SKILLS = (
    "character-casting-lock-board",
    "character-final-lock-board",
    "single-face-character-lock-board",
    "multi-angle-product-identity-lock-board",
    "packaging-product-identity-label-lock-board",
    "material-sensitive-product-master-asset-board",
    "scene-canon-asset-pack",
)

PUBLISH_SURFACE = SKILLS + OWNER_SKILLS

OWNER_EXPORT_CONTRACTS = {
    "character-casting-lock-board": {
        "profile_id": "character_casting",
        "authority_stage": "terminal_character_canon",
        "terminal_route_decision": "casting_as_terminal",
        "profile_markers": ("identity_and_wardrobe", "[identity, wardrobe]", "--casting-as-terminal"),
    },
    "character-final-lock-board": {
        "profile_id": "character_final",
        "authority_stage": "terminal_character_canon",
        "terminal_route_decision": "character_final",
        "profile_markers": ("identity_and_wardrobe", "[identity, wardrobe]"),
    },
    "single-face-character-lock-board": {
        "profile_id": "single_face_character",
        "authority_stage": "terminal_character_canon",
        "terminal_route_decision": "single_face_character",
        "profile_markers": ("identity_and_wardrobe", "[identity, wardrobe]"),
    },
    "multi-angle-product-identity-lock-board": {
        "profile_id": "multi_angle_product",
        "authority_stage": "terminal_product_canon",
        "terminal_route_decision": "not_applicable",
        "profile_markers": ("geometry_only", "[product_geometry]"),
    },
    "packaging-product-identity-label-lock-board": {
        "profile_id": "packaging_product",
        "authority_stage": "terminal_packaging_canon",
        "terminal_route_decision": "not_applicable",
        "profile_markers": (
            "geometry_layout_only", "geometry_layout_exact_copy_verified",
            "[product_geometry]", "[product_geometry, label_copy]",
        ),
    },
    "material-sensitive-product-master-asset-board": {
        "profile_id": "material_sensitive_product",
        "authority_stage": "terminal_material_canon",
        "terminal_route_decision": "not_applicable",
        "profile_markers": ("geometry_and_material", "[product_geometry, material_behavior]"),
    },
    "scene-canon-asset-pack": {
        "profile_id": "scene_canon",
        "authority_stage": "terminal_scene_canon",
        "terminal_route_decision": "not_applicable",
        "profile_markers": ("authority_mode: scene_canon", "[scene_canon]"),
    },
}

PRIMARY_SCHEMAS = {
    "ai-video-shot-script-director": "references/shot_contract.schema.json",
    "ai-video-global-look-lock": "references/global_look_contract.schema.json",
    "ai-video-modular-storyboard": "references/storyboard_manifest.schema.json",
    "ai-video-timed-animatic-previs-director": "references/previs_manifest.schema.json",
    "ai-video-keyframe-continuity-pack": "references/keyframe_manifest.schema.json",
    "ai-video-omni-reference-prompt-director": "references/canonical_ir.schema.json",
}

MARKERS = {
    "ai-video-shot-script-director": (
        ("SKILL.md", "global_directing_prompt_full"),
        ("SKILL.md", "extract_source_document.py"),
        ("references/project_canon_manifest_contract.md", "Apply a delta atomically"),
        ("SKILL.md", "PENDING_PROJECT_CANON_TRANSACTION.json"),
    ),
    "ai-video-global-look-lock": (
        ("SKILL.md", "GLOBAL_LOOK_PROMPT_FULL"),
        ("SKILL.md", "LOOK_STATE"),
        ("references/global_look_contract.schema.json", "look_state_matrix_id"),
        ("references/global_look_contract.schema.json", "state_prompt_full"),
        ("SKILL.md", "PENDING_PROJECT_CANON_TRANSACTION.json"),
    ),
    "ai-video-modular-storyboard": (
        ("SKILL.md", "N independent editable storyboard frames"),
        ("references/storyboard_manifest.schema.json", "structure_draft"),
        ("references/storyboard_manifest.schema.json", "is_model_input_eligible"),
        ("SKILL.md", "MANIFEST_UPDATE_RECEIPT.json"),
        ("SKILL.md", "PENDING_PROJECT_CANON_TRANSACTION.json"),
    ),
    "ai-video-timed-animatic-previs-director": (
        ("SKILL.md", "Timing Animatic V1"),
        ("SKILL.md", "Control Previs V2"),
        ("SKILL.md", "K2 Boundary Supplement"),
        ("SKILL.md", "MANIFEST_UPDATE_RECEIPT.json"),
        ("SKILL.md", "PENDING_PROJECT_CANON_TRANSACTION.json"),
        ("references/provider_runtime_capability_evidence.schema.json", "video_input_constraints"),
        ("scripts/validate_previs_package.py", "validate_live_provider_video_constraints"),
    ),
    "ai-video-keyframe-continuity-pack": (
        ("SKILL.md", "K1 Core Keyframes"),
        ("SKILL.md", "K2 Boundary Supplement"),
        ("references/keyframe_manifest.schema.json", "prompt_file_sha256"),
        ("references/keyframe_manifest.schema.json", "material_state_trajectory"),
        ("SKILL.md", "PENDING_PROJECT_CANON_TRANSACTION.json"),
        ("references/keyframe_manifest.schema.json", "forbidden_video_generation_modes"),
        ("scripts/validate_keyframe_package.py", "classic single-image i2v"),
    ),
    "ai-video-omni-reference-prompt-director": (
        ("SKILL.md", "PROJECT_CANON_PREFLIGHT_INPUT_SNAPSHOT.json"),
        ("SKILL.md", "validate_preflight_package.py"),
        ("SKILL.md", "PROJECT_CANON_COMPILE_INPUT_SNAPSHOT.json"),
        ("SKILL.md", "V1 → K1 core keyframes → P1 unit preflight → K2 boundary supplement → V2 control previs → P2 final compile"),
        ("references/canonical_ir.schema.json", "look_state_prompt_full"),
        ("scripts/validate_prompt_package.py", "FORBIDDEN_PAYLOAD_TOKENS"),
        ("scripts/validate_prompt_package.py", "documented_backend_profile_id"),
        ("SKILL.md", "PENDING_PROJECT_CANON_TRANSACTION.json"),
    ),
}

TEST_COMMANDS = (
    ("shot contract", "ai-video-shot-script-director", "scripts/test_contract.py"),
    ("source ingestion", "ai-video-shot-script-director", "scripts/test_source_ingestion.py"),
    ("project canon manifest", "ai-video-shot-script-director", "scripts/test_project_canon_manifest.py"),
    ("legacy asset canon bridge", "ai-video-shot-script-director", "scripts/test_asset_canon_bridge.py"),
    ("global canon write gate", "ai-video-shot-script-director", "scripts/test_global_canon_write_gate.py"),
    ("global look", "ai-video-global-look-lock", "scripts/test_contract.py"),
    ("storyboard", "ai-video-modular-storyboard", "scripts/test_contract.py"),
    ("previs", "ai-video-timed-animatic-previs-director", "scripts/test_contract.py"),
    ("keyframe", "ai-video-keyframe-continuity-pack", "scripts/test_contract.py"),
    ("prompt preflight", "ai-video-omni-reference-prompt-director", "scripts/test_preflight_contract.py"),
    ("reference atlas", "ai-video-omni-reference-prompt-director", "scripts/test_reference_atlas.py"),
    ("prompt", "ai-video-omni-reference-prompt-director", "scripts/test_contract.py"),
    ("suite contract", "ai-video-omni-reference-prompt-director", "scripts/test_suite_contract.py"),
    ("schema parity", "ai-video-omni-reference-prompt-director", "scripts/validate_schema_parity.py"),
)

SHARED_APPROVALS = ["draft", "assistant_validated", "user_approved", "stale", "blocked"]
GENERATION_ROUTE_MARKERS = (
    "standalone_single_image_to_video: forbidden",
    "ordinary_image_references_in_omni_r2v: allowed",
)
TEXT_SUFFIXES = {".md", ".py", ".json", ".yaml", ".yml", ".txt", ".toml", ".ini", ".cfg", ".sh"}
FORBIDDEN_PATH_PARTS = {"__pycache__", ".DS_Store", ".pytest_cache", ".mypy_cache"}
ABSOLUTE_PATH_RE = re.compile(r"(?<!https:)(?<!http:)/" + r"(?:Volumes|Users)/")
SECRET_RES = (
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"\bgh[opusr]_[A-Za-z0-9]{24,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
)


def walk_json(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk_json(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_json(child)


def _frontmatter_name(text: str) -> str | None:
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---\n", 4)
    if end < 0:
        return None
    match = re.search(r"(?m)^name:\s*([a-z0-9-]+)\s*$", text[4:end])
    return match.group(1) if match else None


def _run(command: list[str], cwd: Path) -> tuple[int, str]:
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=180,
        check=False,
    )
    return result.returncode, result.stdout


def _validate_publication_surface(root: Path, skill: str, errors: list[str]) -> None:
    """Apply the same identity and repository-hygiene gates to all 13 packages."""
    skill_root = root / skill
    if not skill_root.is_dir():
        errors.append(f"{skill}: directory missing")
        return
    skill_md = skill_root / "SKILL.md"
    if not skill_md.is_file():
        errors.append(f"{skill}: required file missing: SKILL.md")
    else:
        try:
            skill_text = skill_md.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            errors.append(f"{skill}: SKILL.md is not UTF-8")
        else:
            if _frontmatter_name(skill_text) != skill:
                errors.append(f"{skill}: SKILL.md frontmatter name mismatch")

    for path in skill_root.rglob("*"):
        if any(part in FORBIDDEN_PATH_PARTS for part in path.parts):
            errors.append(f"{skill}: forbidden generated/cache path: {path.relative_to(root)}")
        if not path.is_file():
            continue
        if path.suffix == ".pyc" or path.name in {".env", "id_rsa", "id_ed25519"}:
            errors.append(f"{skill}: forbidden file: {path.relative_to(root)}")
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            source = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            errors.append(f"{skill}: text file is not UTF-8: {path.relative_to(root)}")
            continue
        if ABSOLUTE_PATH_RE.search(source):
            errors.append(f"{skill}: hardcoded local absolute path: {path.relative_to(root)}")
        if any(pattern.search(source) for pattern in SECRET_RES):
            errors.append(f"{skill}: possible secret/private key in {path.relative_to(root)}")
        if path.suffix.lower() == ".py":
            try:
                compile(source, str(path), "exec")
            except SyntaxError as exc:
                errors.append(f"{skill}: Python syntax error in {path.relative_to(root)}: {exc}")
        if path.suffix.lower() == ".json":
            try:
                json.loads(source, parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)))
            except (json.JSONDecodeError, ValueError) as exc:
                errors.append(f"{skill}: invalid JSON {path.relative_to(root)}: {exc}")


def _validate_owner_export_surface(root: Path, skill: str, errors: list[str]) -> None:
    """Lock each legacy visual owner to its immutable Project Canon bridge profile."""
    skill_root = root / skill
    if not skill_root.is_dir():
        return
    contract = OWNER_EXPORT_CONTRACTS[skill]
    wrapper = skill_root / "scripts/export_ai_video_canon.py"
    if not wrapper.is_file():
        errors.append(f"{skill}: fixed owner export wrapper missing")
    else:
        try:
            wrapper_text = wrapper.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            errors.append(f"{skill}: fixed owner export wrapper is not UTF-8")
        else:
            expected_call = (
                f'run_fixed_owner_cli("{contract["profile_id"]}", Path(__file__))'
            )
            if expected_call not in wrapper_text:
                errors.append(f"{skill}: fixed owner export wrapper profile drift")
            if "from build_asset_canon_export import run_fixed_owner_cli" not in wrapper_text:
                errors.append(f"{skill}: fixed owner export wrapper bypasses the shared bridge")
            if "--owner" in wrapper_text or "argparse" in wrapper_text:
                errors.append(f"{skill}: fixed owner export wrapper exposes an owner override")

    skill_md = skill_root / "SKILL.md"
    if not skill_md.is_file():
        return
    try:
        skill_text = skill_md.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return
    if "## Optional AI-Video Project Canon Export" not in skill_text:
        errors.append(f"{skill}: Project Canon export appendix missing")
    if "../ai-video-shot-script-director/requirements.txt" not in skill_text or "Pillow" not in skill_text:
        errors.append(f"{skill}: pinned Pillow export dependency marker missing")
    for field in ("authority_stage", "terminal_route_decision"):
        expected = contract[field]
        if f"{field}: {expected}" not in skill_text:
            errors.append(f"{skill}: lifecycle marker drift for {field}")
    for marker in contract["profile_markers"]:
        if marker not in skill_text:
            errors.append(f"{skill}: fixed export profile marker missing: {marker}")


def validate_suite(root: Path, run_tests: bool = True, require_discovery: bool = False) -> list[str]:
    root = root.resolve()
    errors: list[str] = []
    for skill in PUBLISH_SURFACE:
        _validate_publication_surface(root, skill, errors)
    for skill in OWNER_SKILLS:
        _validate_owner_export_surface(root, skill, errors)

    for skill in SKILLS:
        skill_root = root / skill
        required = ("SKILL.md", "agents/openai.yaml", "test_cases.md", "scripts/test_contract.py")
        if not skill_root.is_dir():
            continue
        for rel in required:
            if not (skill_root / rel).is_file():
                errors.append(f"{skill}: required file missing: {rel}")
        canon_writer = skill_root / "scripts/apply_project_canon_transition.py"
        if not canon_writer.is_file():
            errors.append(f"{skill}: fixed Project Canon transition wrapper missing")
        else:
            writer_text = canon_writer.read_text(encoding="utf-8")
            if "run_fixed_workflow_canon_writer_cli" not in writer_text:
                errors.append(f"{skill}: Project Canon wrapper bypasses the shared global gate")
        skill_md = skill_root / "SKILL.md"
        if skill_md.is_file():
            text = skill_md.read_text(encoding="utf-8")
            if "Do not use" not in text and "Do not use this Skill" not in text:
                errors.append(f"{skill}: trigger boundary lacks explicit Do not use section")
            for marker in GENERATION_ROUTE_MARKERS:
                if marker not in text:
                    errors.append(f"{skill}: generation-route boundary marker missing: {marker}")
        yaml_path = skill_root / "agents/openai.yaml"
        if yaml_path.is_file():
            yaml_text = yaml_path.read_text(encoding="utf-8")
            for marker in ("display_name:", "short_description:", "default_prompt:", "allow_implicit_invocation:"):
                if marker not in yaml_text:
                    errors.append(f"{skill}: agents/openai.yaml missing {marker}")
            short_match = re.search(r'(?m)^\s*short_description:\s*"([^"]*)"\s*$', yaml_text)
            if short_match is None:
                errors.append(f"{skill}: short_description must be one quoted line")
            elif not 25 <= len(short_match.group(1)) <= 64:
                errors.append(f"{skill}: short_description must contain 25-64 characters")
            if f"${skill}" not in yaml_text:
                errors.append(f"{skill}: default_prompt does not invoke ${skill}")

        schema_path = skill_root / PRIMARY_SCHEMAS[skill]
        if schema_path.is_file():
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
            properties = schema.get("properties", {})
            if properties.get("contract_version", {}).get("const") != "ai-video-artifact-v1":
                errors.append(f"{skill}: primary schema contract_version drift")
            if properties.get("approval_status", {}).get("enum") != SHARED_APPROVALS:
                errors.append(f"{skill}: primary schema approval_status drift")
            for node in walk_json(schema):
                required_fields = node.get("required")
                if isinstance(required_fields, list) and set(required_fields) == {"artifact_id", "owner_skill", "version", "sha256"}:
                    if node.get("additionalProperties") is not False:
                        errors.append(f"{skill}: dependency/artifactRef permits extra properties")

        for rel, marker in MARKERS[skill]:
            marker_path = skill_root / rel
            if not marker_path.is_file() or marker not in marker_path.read_text(encoding="utf-8"):
                errors.append(f"{skill}: contract marker missing in {rel}: {marker}")

    manifest_schema = root / "ai-video-shot-script-director/references/project_canon_manifest.schema.json"
    if not manifest_schema.is_file():
        errors.append("shared PROJECT_CANON_MANIFEST schema missing")
    else:
        manifest = json.loads(manifest_schema.read_text(encoding="utf-8"))
        if manifest.get("properties", {}).get("dependencies", {}).get("maxItems") != 0:
            errors.append("PROJECT_CANON_MANIFEST must have zero envelope dependencies")
        phase_text = json.dumps(manifest, ensure_ascii=False)
        for phase in ("keyframes", "prompt_preflight", "control_previs_v2", "prompt_compile"):
            if phase not in phase_text:
                errors.append(f"PROJECT_CANON_MANIFEST missing phase {phase}")

    workflow = root / "ai-video-omni-reference-prompt-director/references/ai_video_suite_workflow.md"
    if workflow.is_file():
        workflow_text = workflow.read_text(encoding="utf-8")
        workflow_lower = workflow_text.lower()
        for banned_boundary in (
            "text-only video generation", "single-image-to-video",
            "first/last/start/end/endpoint-frame", "music",
            "standalone_single_image_to_video", "ordinary_image_references_in_omni_r2v",
        ):
            if banned_boundary.lower() not in workflow_lower:
                errors.append(f"suite workflow does not state excluded boundary: {banned_boundary}")
    else:
        errors.append("suite workflow missing")

    shot_requirements = root / "ai-video-shot-script-director/requirements.txt"
    prompt_requirements = root / "ai-video-omni-reference-prompt-director/requirements.txt"
    pillow_pins: dict[str, str] = {}
    for label, path in (("Shot Director", shot_requirements), ("Prompt Director", prompt_requirements)):
        if not path.is_file():
            errors.append(f"{label}: requirements.txt missing")
            continue
        pins = [
            line.strip() for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip().lower().startswith("pillow") and not line.lstrip().startswith("#")
        ]
        if len(pins) != 1 or not re.fullmatch(r"Pillow==[0-9]+\.[0-9]+\.[0-9]+", pins[0]):
            errors.append(f"{label}: Pillow must have one exact == version pin")
        else:
            pillow_pins[label] = pins[0]
    if len(pillow_pins) == 2 and len(set(pillow_pins.values())) != 1:
        errors.append("Shot Director and Prompt Director Pillow pins must remain identical")

    if run_tests:
        for label, skill, rel in TEST_COMMANDS:
            code, output = _run([sys.executable, rel], root / skill)
            if code != 0:
                errors.append(f"{label} self-test failed (exit {code}): {output[-1500:].strip()}")

    if require_discovery:
        discovery_root = Path.home() / ".codex" / "skills"
        for skill in PUBLISH_SURFACE:
            link = discovery_root / skill
            expected = (root / skill).resolve()
            if not link.is_symlink():
                errors.append(f"{skill}: discovery symlink missing")
            elif link.resolve() != expected:
                errors.append(f"{skill}: discovery symlink targets {link.resolve()}, expected {expected}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    default_root = Path(__file__).resolve().parents[2]
    parser.add_argument("--suite-root", type=Path, default=default_root)
    parser.add_argument("--skip-tests", action="store_true")
    parser.add_argument("--require-discovery", action="store_true")
    args = parser.parse_args()
    try:
        errors = validate_suite(args.suite_root, not args.skip_tests, args.require_discovery)
    except Exception as exc:  # total-function CLI guard for damaged repositories
        print(f"ERROR: suite validation could not complete safely: {type(exc).__name__}: {exc}")
        return 2
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(
        "OK: six-skill AI video suite and 13-package publication surface "
        f"validated at {args.suite_root.resolve()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
