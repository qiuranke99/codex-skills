#!/usr/bin/env python3
"""Shared, package-local validators for the material board v4 artifact chain."""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
from pathlib import Path
from typing import Any, Callable, Iterable

try:
    from PIL import Image, ImageSequence, UnidentifiedImageError
except ImportError as exc:  # pragma: no cover - exercised by the installed runtime gate
    Image = None  # type: ignore[assignment]
    ImageSequence = None  # type: ignore[assignment]
    UnidentifiedImageError = OSError  # type: ignore[assignment,misc]
    _PIL_IMPORT_ERROR: ImportError | None = exc
else:
    _PIL_IMPORT_ERROR = None


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
ID_RE = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")
ATTEMPT_RE = re.compile(r"^(?:01|02|03)$")
ALIAS_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")

FORMAT_METADATA: dict[str, tuple[str, str]] = {
    "PNG": ("image/png", ".png"),
    "JPEG": ("image/jpeg", ".jpg"),
    "WEBP": ("image/webp", ".webp"),
    "TIFF": ("image/tiff", ".tif"),
    "GIF": ("image/gif", ".gif"),
    "BMP": ("image/bmp", ".bmp"),
}

ALLOWED_SOURCE_AUTHORITIES = {"authoritative_source", "supporting_source"}
ALLOWED_SOURCE_USES = {
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
}
INVARIANT_CATEGORIES = {
    "identity",
    "topology",
    "structure",
    "material",
    "color",
    "label_layout",
    "state",
}
PANEL_ROLES = {
    "primary_anchor",
    "multi_angle",
    "material_response",
    "critical_structure",
    "label_micro",
    "state_window",
}

ROLE_REQUIRED_USES: dict[str, set[str]] = {
    "primary_anchor": {"identity", "silhouette", "proportions"},
    "multi_angle": {"identity", "silhouette", "proportions"},
    "material_response": {"material"},
    "critical_structure": {"structure", "topology"},
    "label_micro": {"label_layout"},
    "state_window": {"state"},
}


class MaterialContractError(RuntimeError):
    """Stable artifact-contract error used by package-local entrypoints."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail


class _DuplicateKey(ValueError):
    pass


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def pretty_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def render_4k_enhancement_prompt_bytes(
    *,
    board_path: Path,
    board_sha256: str,
    source_references: list[dict[str, str]],
    source_contract_path: Path,
    source_contract_sha256: str,
    cleanup_defects: list[dict[str, Any]],
) -> bytes:
    """Render the only accepted 4K prompt so prose cannot expand cleanup scope."""
    directives = [
        {
            "defect_id": defect["defect_id"],
            "cleanup_operation": defect["cleanup_operation"],
            "panel_ids": defect["panel_ids"],
            "source_aliases": defect["source_aliases"],
        }
        for defect in cleanup_defects
    ]
    return pretty_json_bytes(
        {
            "schema_version": "material_4k_enhancement_prompt.v2",
            "task": "Upscale the accepted board while applying only the enumerated raster cleanup directives.",
            "accepted_board": {"path": str(board_path), "sha256": board_sha256},
            "original_source_references": source_references,
            "source_contract": {
                "path": str(source_contract_path),
                "sha256": source_contract_sha256,
            },
            "allowed_cleanup_directives": directives,
            "requested_output": {"aspect_ratio": "16:9", "image_size": "4K"},
            "preservation_contract": {
                "no_unlisted_cleanup": True,
                "preserve": [
                    "product_identity",
                    "silhouette",
                    "proportions",
                    "component_order",
                    "chain_and_link_rhythm",
                    "connector_topology",
                    "structure",
                    "edge_thickness",
                    "fill_boundary",
                    "material_state",
                    "label_identity",
                    "facets",
                    "highlights",
                    "material_microdetail",
                    "panel_topology",
                    "panel_order",
                    "framing",
                ],
                "forbid": [
                    "crop",
                    "stretch",
                    "reframe",
                    "panel_reorder",
                    "panel_addition",
                    "advertising_treatment",
                    "non_product_native_text",
                ],
            },
        }
    )


def normalized_path(path: Path) -> str:
    return os.path.normcase(os.path.abspath(os.fspath(path.expanduser().resolve(strict=False))))


def lexical_normalized_path(path: Path) -> str:
    """Normalize spelling without following the final path or any parent link."""
    return os.path.normcase(os.path.abspath(os.path.normpath(os.fspath(path.expanduser()))))


def require_inside(root: Path, path: Path, code: str, label: str) -> Path:
    root_resolved = root.expanduser().resolve(strict=False)
    path_resolved = path.expanduser().resolve(strict=False)
    try:
        common = os.path.commonpath([normalized_path(root_resolved), normalized_path(path_resolved)])
    except ValueError as exc:
        raise MaterialContractError(code, f"{label} containment failed: {exc}") from exc
    if common != normalized_path(root_resolved):
        raise MaterialContractError(code, f"{label} is outside {root_resolved}: {path_resolved}")
    return path_resolved


def require_exact_path(actual: Path, expected: Path, code: str, label: str) -> Path:
    actual_lexical = lexical_normalized_path(actual)
    expected_lexical = lexical_normalized_path(expected)
    if actual_lexical != expected_lexical:
        raise MaterialContractError(code, f"{label} must be exactly {expected_lexical}")
    actual_resolved = actual.expanduser().resolve(strict=False)
    if normalized_path(actual_resolved) != expected_lexical:
        raise MaterialContractError(
            code,
            f"{label} must not resolve through a symlink or junction: {actual_resolved}",
        )
    return actual_resolved


def _pairs_without_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKey(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def strict_json_object(data: bytes, code: str, label: str) -> dict[str, Any]:
    if not data or data.startswith(b"\xef\xbb\xbf") or b"\r" in data:
        raise MaterialContractError(code, f"{label} must be non-empty UTF-8/LF without BOM")
    try:
        value = json.loads(data.decode("utf-8"), object_pairs_hook=_pairs_without_duplicates)
    except (UnicodeDecodeError, json.JSONDecodeError, _DuplicateKey) as exc:
        raise MaterialContractError(code, f"invalid {label}: {exc}") from exc
    if not isinstance(value, dict):
        raise MaterialContractError(code, f"{label} must be a JSON object")
    return value


def load_json_file(path: Path, code: str, label: str) -> tuple[dict[str, Any], bytes]:
    if not path.is_file():
        raise MaterialContractError(code, f"{label} is missing: {path}")
    data = path.read_bytes()
    return strict_json_object(data, code, label), data


def require_exact_keys(
    value: dict[str, Any], required: set[str], code: str, label: str
) -> None:
    missing = sorted(required - set(value))
    unknown = sorted(set(value) - required)
    if missing or unknown:
        raise MaterialContractError(
            code,
            f"{label} keys mismatch; missing={missing}, unknown={unknown}",
        )


def create_only_bytes(
    path: Path,
    data: bytes,
    *,
    code: str,
    idempotent: bool,
) -> bool:
    """Create bytes without replacement. Return True when newly created."""
    if path.exists():
        if idempotent and path.is_file() and path.read_bytes() == data:
            return False
        raise MaterialContractError(code, f"create-only destination already exists: {path}")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_BINARY"):
        flags |= os.O_BINARY
    descriptor = os.open(path, flags, 0o600)
    try:
        with os.fdopen(descriptor, "wb", closefd=True) as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
        raise
    return True


def inspect_image_bytes(
    data: bytes,
    *,
    code: str,
    label: str,
    required_format: str | None = None,
) -> dict[str, Any]:
    """Use Pillow verify plus a fresh full load, including every animated frame."""
    if _PIL_IMPORT_ERROR is not None:
        raise MaterialContractError(
            "blocked_material_decoder_unavailable",
            f"Pillow is required for material-board image validation: {_PIL_IMPORT_ERROR}",
        )
    try:
        with Image.open(io.BytesIO(data)) as verify_image:
            detected_format = verify_image.format
            verify_image.verify()
        with Image.open(io.BytesIO(data)) as loaded_image:
            loaded_format = loaded_image.format
            width, height = loaded_image.size
            mode = loaded_image.mode
            frame_count = int(getattr(loaded_image, "n_frames", 1))
            for frame in ImageSequence.Iterator(loaded_image):
                frame.load()
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError) as exc:
        raise MaterialContractError(code, f"{label} is not a fully decodable image: {exc}") from exc
    if detected_format != loaded_format or loaded_format not in FORMAT_METADATA:
        raise MaterialContractError(code, f"{label} has unsupported or unstable format: {loaded_format!r}")
    if required_format is not None and loaded_format != required_format:
        raise MaterialContractError(
            code,
            f"{label} must decode as {required_format}, got {loaded_format}",
        )
    if width <= 0 or height <= 0 or frame_count <= 0:
        raise MaterialContractError(code, f"{label} has invalid dimensions or frame count")
    mime_type, canonical_suffix = FORMAT_METADATA[loaded_format]
    return {
        "detected_format": loaded_format,
        "mime_type": mime_type,
        "canonical_suffix": canonical_suffix,
        "width_px": width,
        "height_px": height,
        "mode": mode,
        "frame_count": frame_count,
    }


def load_reference_manifest(manifest_path: Path, run_dir: Path) -> dict[str, Any]:
    code = "blocked_reference_manifest_invalid"
    run_dir = run_dir.expanduser().resolve(strict=False)
    manifest_path = require_exact_path(
        manifest_path,
        run_dir / "sources" / "reference-manifest.json",
        code,
        "reference manifest",
    )
    manifest, manifest_bytes = load_json_file(manifest_path, code, "reference manifest")
    if manifest.get("schema_version") == "material_reference_bundle.v1":
        raise MaterialContractError(
            "blocked_legacy_material_run_v1",
            "material_reference_bundle.v1 cannot be resumed as a v4 run",
        )
    required_manifest_keys = {
        "schema_version",
        "immutability_contract",
        "run_dir_realpath",
        "reference_root_realpath",
        "ordered_references",
        "ordered_bundle_sha256",
    }
    require_exact_keys(manifest, required_manifest_keys, code, "reference manifest")
    if manifest["schema_version"] != "material_reference_bundle.v2":
        raise MaterialContractError(code, "unexpected reference manifest schema")
    reference_root = require_exact_path(
        run_dir / "sources" / "references",
        run_dir / "sources" / "references",
        code,
        "reference root",
    )
    if manifest["run_dir_realpath"] != str(run_dir) or manifest["reference_root_realpath"] != str(reference_root):
        raise MaterialContractError(code, "reference manifest realpath locks do not match this run")
    entries = manifest["ordered_references"]
    if not isinstance(entries, list) or not entries:
        raise MaterialContractError(code, "ordered_references must be non-empty")

    aliases: list[str] = []
    paths: list[Path] = []
    hashes: list[str] = []
    required_entry_keys = {
        "index",
        "alias",
        "source_realpath",
        "frozen_path",
        "size_bytes",
        "sha256",
        "detected_format",
        "mime_type",
        "canonical_suffix",
        "width_px",
        "height_px",
        "mode",
        "frame_count",
    }
    for expected_index, entry in enumerate(entries, 1):
        if not isinstance(entry, dict):
            raise MaterialContractError(code, "reference entry must be an object")
        require_exact_keys(entry, required_entry_keys, code, "reference entry")
        alias = entry["alias"]
        if entry["index"] != expected_index or not isinstance(alias, str) or not ALIAS_RE.fullmatch(alias):
            raise MaterialContractError(code, "reference index or alias is invalid")
        frozen_raw = entry["frozen_path"]
        if not isinstance(frozen_raw, str) or not Path(frozen_raw).is_absolute():
            raise MaterialContractError(code, "frozen reference path must be absolute")
        suffix = entry["canonical_suffix"]
        if not isinstance(suffix, str) or suffix not in {item[1] for item in FORMAT_METADATA.values()}:
            raise MaterialContractError(code, "frozen reference canonical suffix is invalid")
        frozen = require_exact_path(
            Path(frozen_raw),
            reference_root / f"{expected_index:02d}_{alias}{suffix}",
            code,
            "frozen reference",
        )
        if frozen.parent != reference_root or frozen.name != f"{expected_index:02d}_{alias}{suffix}":
            raise MaterialContractError(code, "frozen reference filename is not canonical")
        if not frozen.is_file():
            raise MaterialContractError(code, f"frozen reference is missing: {frozen}")
        data = frozen.read_bytes()
        expected_sha = entry["sha256"]
        if (
            type(entry["size_bytes"]) is not int
            or entry["size_bytes"] != len(data)
            or not isinstance(expected_sha, str)
            or not SHA256_RE.fullmatch(expected_sha)
            or sha256_bytes(data) != expected_sha
        ):
            raise MaterialContractError(code, f"frozen reference bytes changed: {frozen}")
        metadata = inspect_image_bytes(data, code=code, label=f"frozen reference {alias}")
        for field in (
            "detected_format",
            "mime_type",
            "canonical_suffix",
            "width_px",
            "height_px",
            "mode",
            "frame_count",
        ):
            if entry[field] != metadata[field]:
                raise MaterialContractError(code, f"frozen reference metadata changed: {alias}.{field}")
        aliases.append(alias)
        paths.append(frozen)
        hashes.append(expected_sha)
    if len(set(aliases)) != len(aliases) or len(set(map(normalized_path, paths))) != len(paths):
        raise MaterialContractError(code, "reference aliases and paths must be unique")
    if len(set(hashes)) != len(hashes):
        raise MaterialContractError(code, "byte-identical duplicate references are forbidden")
    bundle_sha = sha256_bytes(canonical_json_bytes(entries))
    if manifest["ordered_bundle_sha256"] != bundle_sha:
        raise MaterialContractError(code, "ordered reference bundle hash mismatch")
    return {
        "value": manifest,
        "bytes": manifest_bytes,
        "sha256": sha256_bytes(manifest_bytes),
        "entries": entries,
        "paths": paths,
        "aliases": aliases,
        "hashes": hashes,
        "ordered_bundle_sha256": bundle_sha,
    }


def _one_line(value: Any, code: str, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or any(char in value for char in "\r\n\x00"):
        raise MaterialContractError(code, f"{label} must be one non-empty line")
    return value.strip()


def _string_list(
    value: Any,
    *,
    code: str,
    label: str,
    allow_empty: bool,
    allowed: set[str] | None = None,
) -> list[str]:
    if not isinstance(value, list) or (not allow_empty and not value):
        raise MaterialContractError(code, f"{label} must be {'a' if allow_empty else 'a non-empty'} list")
    result = [_one_line(item, code, label) for item in value]
    if len(set(result)) != len(result):
        raise MaterialContractError(code, f"{label} must contain unique values")
    if allowed is not None and not set(result) <= allowed:
        raise MaterialContractError(code, f"{label} contains unsupported values: {sorted(set(result) - allowed)}")
    return result


def normalize_source_contract_draft(
    draft: dict[str, Any], manifest_record: dict[str, Any]
) -> dict[str, Any]:
    code = "blocked_material_source_contract_invalid"
    required = {
        "schema_version",
        "asset_id",
        "source_authority",
        "fact_registry",
        "critical_invariants",
        "panel_plan",
    }
    require_exact_keys(draft, required, code, "material source contract draft")
    if draft["schema_version"] != "material_source_contract_draft.v1":
        raise MaterialContractError(code, "unexpected source-contract draft schema")
    asset_id = _one_line(draft["asset_id"], code, "asset_id")
    if not ID_RE.fullmatch(asset_id):
        raise MaterialContractError(code, "asset_id must use lowercase identifier syntax")

    source_authority_raw = draft["source_authority"]
    if not isinstance(source_authority_raw, list) or not source_authority_raw:
        raise MaterialContractError(code, "source_authority must be non-empty")
    source_authority: list[dict[str, Any]] = []
    authority_aliases: list[str] = []
    for entry in source_authority_raw:
        if not isinstance(entry, dict):
            raise MaterialContractError(code, "source authority entry must be an object")
        require_exact_keys(entry, {"alias", "authority", "allowed_uses", "exclusions"}, code, "source authority entry")
        alias = _one_line(entry["alias"], code, "source alias")
        authority = _one_line(entry["authority"], code, "source authority")
        if authority not in ALLOWED_SOURCE_AUTHORITIES:
            raise MaterialContractError(code, f"unsupported source authority: {authority}")
        allowed_uses = _string_list(
            entry["allowed_uses"], code=code, label="allowed_uses", allow_empty=False, allowed=ALLOWED_SOURCE_USES
        )
        exclusions = _string_list(
            entry["exclusions"], code=code, label="exclusions", allow_empty=True
        )
        source_authority.append(
            {
                "alias": alias,
                "authority": authority,
                "allowed_uses": sorted(allowed_uses),
                "exclusions": exclusions,
            }
        )
        authority_aliases.append(alias)
    if authority_aliases != manifest_record["aliases"]:
        raise MaterialContractError(
            code,
            "source_authority aliases must exactly equal manifest order with one entry per source",
        )
    authority_by_alias = {entry["alias"]: entry for entry in source_authority}

    registry = draft["fact_registry"]
    if not isinstance(registry, dict):
        raise MaterialContractError(code, "fact_registry must be an object")
    require_exact_keys(registry, {"verified", "inferred", "needs_source"}, code, "fact_registry")
    normalized_registry: dict[str, list[dict[str, Any]]] = {}
    fact_classes: dict[str, str] = {}
    fact_sources: dict[str, list[str]] = {}
    for classification in ("verified", "inferred", "needs_source"):
        raw_entries = registry[classification]
        if not isinstance(raw_entries, list):
            raise MaterialContractError(code, f"fact_registry.{classification} must be a list")
        normalized_entries: list[dict[str, Any]] = []
        for fact in raw_entries:
            if not isinstance(fact, dict):
                raise MaterialContractError(code, "fact entry must be an object")
            require_exact_keys(fact, {"fact_id", "statement", "source_aliases"}, code, "fact entry")
            fact_id = _one_line(fact["fact_id"], code, "fact_id")
            if not ID_RE.fullmatch(fact_id) or fact_id in fact_classes:
                raise MaterialContractError(code, f"fact_id is invalid or duplicated: {fact_id}")
            statement = _one_line(fact["statement"], code, "fact statement")
            aliases = _string_list(
                fact["source_aliases"], code=code, label="fact source_aliases", allow_empty=classification == "needs_source"
            )
            if not set(aliases) <= set(manifest_record["aliases"]):
                raise MaterialContractError(code, f"fact {fact_id} references an unknown source alias")
            fact_classes[fact_id] = classification
            fact_sources[fact_id] = aliases
            normalized_entries.append(
                {"fact_id": fact_id, "statement": statement, "source_aliases": aliases}
            )
        normalized_registry[classification] = normalized_entries
    if not normalized_registry["verified"]:
        raise MaterialContractError(code, "at least one verified fact is required")

    raw_invariants = draft["critical_invariants"]
    if not isinstance(raw_invariants, list) or not raw_invariants:
        raise MaterialContractError(code, "critical_invariants must be non-empty")
    invariants: list[dict[str, Any]] = []
    invariant_ids: list[str] = []
    for invariant in raw_invariants:
        if not isinstance(invariant, dict):
            raise MaterialContractError(code, "critical invariant must be an object")
        require_exact_keys(
            invariant,
            {"invariant_id", "category", "fact_id", "required_for_acceptance"},
            code,
            "critical invariant",
        )
        invariant_id = _one_line(invariant["invariant_id"], code, "invariant_id")
        category = _one_line(invariant["category"], code, "invariant category")
        fact_id = _one_line(invariant["fact_id"], code, "invariant fact_id")
        if not ID_RE.fullmatch(invariant_id) or invariant_id in invariant_ids:
            raise MaterialContractError(code, f"invariant_id is invalid or duplicated: {invariant_id}")
        if category not in INVARIANT_CATEGORIES or fact_id not in fact_classes:
            raise MaterialContractError(code, f"invariant {invariant_id} has invalid category or fact")
        if fact_classes[fact_id] != "verified":
            raise MaterialContractError(
                code,
                f"critical invariant {invariant_id} must bind a verified fact, not {fact_classes[fact_id]}",
            )
        if not fact_sources[fact_id]:
            raise MaterialContractError(code, f"critical invariant {invariant_id} has no source evidence")
        unsupported_fact_sources = [
            alias
            for alias in fact_sources[fact_id]
            if category not in authority_by_alias[alias]["allowed_uses"]
        ]
        if unsupported_fact_sources:
            raise MaterialContractError(
                code,
                f"critical invariant {invariant_id} uses sources not authorized for {category}: "
                f"{unsupported_fact_sources}",
            )
        if invariant["required_for_acceptance"] is not True:
            raise MaterialContractError(code, "every critical invariant must be required_for_acceptance=true")
        invariants.append(
            {
                "invariant_id": invariant_id,
                "category": category,
                "fact_id": fact_id,
                "evidence_classification": fact_classes[fact_id],
                "required_for_acceptance": True,
            }
        )
        invariant_ids.append(invariant_id)

    raw_panels = draft["panel_plan"]
    if not isinstance(raw_panels, list) or not 7 <= len(raw_panels) <= 10:
        raise MaterialContractError(code, "panel_plan must contain 7-10 panels")
    panel_plan: list[dict[str, Any]] = []
    panel_ids: list[str] = []
    roles: list[str] = []
    covered_invariants: set[str] = set()
    for panel in raw_panels:
        if not isinstance(panel, dict):
            raise MaterialContractError(code, "panel entry must be an object")
        require_exact_keys(
            panel,
            {
                "panel_id",
                "role",
                "evidence_job",
                "source_aliases",
                "invariant_ids",
                "required_for_acceptance",
            },
            code,
            "panel entry",
        )
        panel_id = _one_line(panel["panel_id"], code, "panel_id")
        role = _one_line(panel["role"], code, "panel role")
        evidence_job = _one_line(panel["evidence_job"], code, "panel evidence_job")
        source_aliases = _string_list(
            panel["source_aliases"], code=code, label="panel source_aliases", allow_empty=False
        )
        panel_invariants = _string_list(
            panel["invariant_ids"], code=code, label="panel invariant_ids", allow_empty=False
        )
        if not ID_RE.fullmatch(panel_id) or panel_id in panel_ids or role not in PANEL_ROLES:
            raise MaterialContractError(code, f"panel_id or role is invalid: {panel_id}/{role}")
        if panel["required_for_acceptance"] is not True:
            raise MaterialContractError(code, "every planned panel must be required_for_acceptance=true")
        if not set(source_aliases) <= set(manifest_record["aliases"]):
            raise MaterialContractError(code, f"panel {panel_id} references an unknown source alias")
        if not set(panel_invariants) <= set(invariant_ids):
            raise MaterialContractError(code, f"panel {panel_id} references an unknown invariant")
        unauthorized_composition_sources = [
            alias
            for alias in source_aliases
            if "panel_composition" not in authority_by_alias[alias]["allowed_uses"]
        ]
        if unauthorized_composition_sources:
            raise MaterialContractError(
                code,
                f"panel {panel_id} uses sources excluded from panel composition: "
                f"{unauthorized_composition_sources}",
            )
        panel_allowed_uses = {
            use for alias in source_aliases for use in authority_by_alias[alias]["allowed_uses"]
        }
        role_required = ROLE_REQUIRED_USES[role]
        if role == "critical_structure":
            role_supported = bool(panel_allowed_uses & role_required)
        else:
            role_supported = role_required <= panel_allowed_uses
        if not role_supported:
            raise MaterialContractError(
                code,
                f"panel {panel_id} sources do not authorize the {role} evidence job; "
                f"required uses={sorted(role_required)}",
            )
        invariant_by_id = {item["invariant_id"]: item for item in invariants}
        required_fact_sources = {
            alias
            for invariant_id in panel_invariants
            for alias in fact_sources[invariant_by_id[invariant_id]["fact_id"]]
        }
        if not required_fact_sources <= set(source_aliases):
            raise MaterialContractError(
                code,
                f"panel {panel_id} omits source aliases required by its invariants: "
                f"{sorted(required_fact_sources - set(source_aliases))}",
            )
        panel_plan.append(
            {
                "panel_id": panel_id,
                "role": role,
                "evidence_job": evidence_job,
                "source_aliases": source_aliases,
                "invariant_ids": panel_invariants,
                "required_for_acceptance": True,
            }
        )
        panel_ids.append(panel_id)
        roles.append(role)
        covered_invariants.update(panel_invariants)
    if roles.count("primary_anchor") != 1 or not 3 <= roles.count("multi_angle") <= 4:
        raise MaterialContractError(code, "panel_plan requires one primary_anchor and 3-4 multi_angle panels")
    if roles.count("material_response") < 1 or roles.count("label_micro") > 1 or roles.count("state_window") > 1:
        raise MaterialContractError(code, "panel role cardinality is invalid")
    if covered_invariants != set(invariant_ids):
        raise MaterialContractError(code, "every critical invariant must be covered by at least one panel")

    return {
        "schema_version": "material_source_contract.v1",
        "asset_id": asset_id,
        "reference_manifest_path": "",
        "reference_manifest_sha256": manifest_record["sha256"],
        "ordered_reference_bundle_sha256": manifest_record["ordered_bundle_sha256"],
        "source_authority": source_authority,
        "fact_registry": normalized_registry,
        "critical_invariants": invariants,
        "panel_plan": panel_plan,
    }


def source_contract_core(contract: dict[str, Any]) -> dict[str, Any]:
    keys = {
        "schema_version",
        "asset_id",
        "reference_manifest_path",
        "reference_manifest_sha256",
        "ordered_reference_bundle_sha256",
        "source_authority",
        "fact_registry",
        "critical_invariants",
        "panel_plan",
    }
    return {key: contract[key] for key in sorted(keys)}


def render_material_prompt_block(core: dict[str, Any], core_sha256: str) -> bytes:
    lines = [
        "[MATERIAL_SOURCE_CONTRACT_V1]",
        f"asset_id: {core['asset_id']}",
        f"contract_core_sha256: {core_sha256}",
        f"reference_manifest_sha256: {core['reference_manifest_sha256']}",
        "SOURCE_AUTHORITY:",
    ]
    for source in core["source_authority"]:
        exclusions = "; ".join(source["exclusions"]) if source["exclusions"] else "none"
        lines.append(
            f"- {source['alias']} | authority={source['authority']} | allowed_uses={','.join(source['allowed_uses'])} | exclusions={exclusions}"
        )
    for classification, heading in (
        ("verified", "VERIFIED_FACTS"),
        ("inferred", "INFERRED_FACTS_DO_NOT_UPGRADE"),
        ("needs_source", "NEEDS_SOURCE_OMIT_OR_MARK_UNRESOLVED"),
    ):
        lines.append(f"{heading}:")
        facts = core["fact_registry"][classification]
        if not facts:
            lines.append("- none")
        for fact in facts:
            aliases = ",".join(fact["source_aliases"]) if fact["source_aliases"] else "none"
            lines.append(f"- {fact['fact_id']} | sources={aliases} | {fact['statement']}")
    lines.append("CRITICAL_INVARIANTS:")
    for invariant in core["critical_invariants"]:
        lines.append(
            f"- {invariant['invariant_id']} | category={invariant['category']} | fact={invariant['fact_id']} | evidence={invariant['evidence_classification']} | preserve exactly"
        )
    lines.append("PANEL_PLAN:")
    for panel in core["panel_plan"]:
        lines.append(
            f"- {panel['panel_id']} | role={panel['role']} | sources={','.join(panel['source_aliases'])} | invariants={','.join(panel['invariant_ids'])} | {panel['evidence_job']}"
        )
    lines.extend(
        [
            "Do not invent, merge, upgrade, or visually repair inferred or needs_source facts.",
            "[/MATERIAL_SOURCE_CONTRACT_V1]",
            "",
        ]
    )
    return "\n".join(lines).encode("utf-8")


def load_source_contract(
    contract_path: Path,
    run_dir: Path,
    manifest_record: dict[str, Any],
) -> dict[str, Any]:
    code = "blocked_material_source_contract_invalid"
    run_dir = run_dir.expanduser().resolve(strict=False)
    contract_path = require_exact_path(
        contract_path,
        run_dir / "sources" / "material-source-contract.json",
        code,
        "material source contract",
    )
    contract, contract_bytes = load_json_file(contract_path, code, "material source contract")
    if contract.get("schema_version") != "material_source_contract.v1":
        raise MaterialContractError(code, "unexpected material source contract schema")
    required = {
        "schema_version",
        "asset_id",
        "reference_manifest_path",
        "reference_manifest_sha256",
        "ordered_reference_bundle_sha256",
        "source_authority",
        "fact_registry",
        "critical_invariants",
        "panel_plan",
        "contract_core_sha256",
        "prompt_block_path",
        "prompt_block_sha256",
        "immutability_contract",
    }
    require_exact_keys(contract, required, code, "material source contract")
    if normalized_path(Path(contract["reference_manifest_path"])) != normalized_path(
        run_dir / "sources" / "reference-manifest.json"
    ):
        raise MaterialContractError(code, "source contract binds the wrong reference manifest path")
    if (
        contract["reference_manifest_sha256"] != manifest_record["sha256"]
        or contract["ordered_reference_bundle_sha256"] != manifest_record["ordered_bundle_sha256"]
    ):
        raise MaterialContractError(code, "source contract reference-manifest lock mismatch")
    core = source_contract_core(contract)
    core_sha = sha256_bytes(canonical_json_bytes(core))
    if contract["contract_core_sha256"] != core_sha:
        raise MaterialContractError(code, "source contract core hash mismatch")
    block_path = require_exact_path(
        Path(contract["prompt_block_path"]),
        run_dir / "sources" / "material-prompt-block.md",
        code,
        "material prompt block",
    )
    if not block_path.is_file():
        raise MaterialContractError(code, f"material prompt block is missing: {block_path}")
    block_bytes = block_path.read_bytes()
    expected_block = render_material_prompt_block(core, core_sha)
    if block_bytes != expected_block or contract["prompt_block_sha256"] != sha256_bytes(block_bytes):
        raise MaterialContractError(code, "material prompt block bytes/hash do not match the source contract")
    if contract["immutability_contract"] != "create_only_idempotent;rehash_at_every_transition":
        raise MaterialContractError(code, "unexpected source-contract immutability contract")
    # Re-run semantic normalization from the frozen fields so mutated ledgers fail closed.
    draft_view = {
        "schema_version": "material_source_contract_draft.v1",
        "asset_id": contract["asset_id"],
        "source_authority": contract["source_authority"],
        "fact_registry": {
            classification: [
                {
                    "fact_id": fact["fact_id"],
                    "statement": fact["statement"],
                    "source_aliases": fact["source_aliases"],
                }
                for fact in contract["fact_registry"][classification]
            ]
            for classification in ("verified", "inferred", "needs_source")
        },
        "critical_invariants": [
            {
                "invariant_id": item["invariant_id"],
                "category": item["category"],
                "fact_id": item["fact_id"],
                "required_for_acceptance": item["required_for_acceptance"],
            }
            for item in contract["critical_invariants"]
        ],
        "panel_plan": contract["panel_plan"],
    }
    normalized = normalize_source_contract_draft(draft_view, manifest_record)
    normalized["reference_manifest_path"] = str(run_dir / "sources" / "reference-manifest.json")
    if source_contract_core(normalized) != core:
        raise MaterialContractError(code, "source contract semantic normalization mismatch")
    return {
        "value": contract,
        "bytes": contract_bytes,
        "sha256": sha256_bytes(contract_bytes),
        "core": core,
        "core_sha256": core_sha,
        "prompt_block_path": block_path,
        "prompt_block_bytes": block_bytes,
        "prompt_block_sha256": sha256_bytes(block_bytes),
    }


def read_prompt_bytes(path: Path, code: str, label: str) -> bytes:
    if not path.is_file():
        raise MaterialContractError(code, f"{label} is missing: {path}")
    data = path.read_bytes()
    if not data or data.startswith(b"\xef\xbb\xbf") or b"\r" in data:
        raise MaterialContractError(code, f"{label} must be non-empty UTF-8/LF without BOM")
    try:
        data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise MaterialContractError(code, f"{label} is not UTF-8: {exc}") from exc
    return data


def require_prompt_block_once(prompt_bytes: bytes, block_bytes: bytes, code: str) -> None:
    if prompt_bytes.count(block_bytes) != 1:
        raise MaterialContractError(code, "generation prompt must contain the exact material prompt block once")


def render_worker_exec_bytes(
    worker_run_nonce: str,
    prompt_text: str,
    referenced_image_paths: Iterable[Path],
) -> bytes:
    arguments = {
        "prompt": prompt_text,
        "referenced_image_paths": [str(path) for path in referenced_image_paths],
    }
    argument_json = json.dumps(arguments, ensure_ascii=False, separators=(",", ":"))
    source = (
        f'const worker_run_nonce = "{worker_run_nonce}";\n'
        f"const result = await tools.image_gen__imagegen({argument_json});\n"
        "generatedImage(result);\n"
    )
    return source.encode("utf-8")


def map_contract_error(
    exc: MaterialContractError,
    mapper: Callable[[str], str] | None = None,
) -> MaterialContractError:
    if mapper is None:
        return exc
    return MaterialContractError(mapper(exc.code), exc.detail)
