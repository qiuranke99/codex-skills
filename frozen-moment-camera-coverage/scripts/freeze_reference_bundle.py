#!/usr/bin/env python3
"""Freeze ordered source references into a run-scoped frozen-moment bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Any

from PIL import Image, UnidentifiedImageError


ROLES = {
    "moment_anchor",
    "identity_anchor",
    "wardrobe_anchor",
    "scene_topology_anchor",
    "look_anchor",
}
RIGHTS_STATES = {"user_supplied", "owned", "licensed", "public_reference_only", "unknown"}
DEFAULT_SCOPES = {
    "moment_anchor": ("visible moment, pose, contacts, scene, world-space light, look", "unseen facts as recovered reality"),
    "identity_anchor": ("identity, visible age, body proportions, hair", "pose, gaze, expression, action"),
    "wardrobe_anchor": ("garment structure, material, color, asymmetry", "pose, wearing state, scene"),
    "scene_topology_anchor": ("architecture, object positions, spatial relations", "identity, action, relighting"),
    "look_anchor": ("palette, contrast, grain, optical character", "identity, wardrobe, scene content"),
}
SHA_RE = re.compile(r"^[0-9a-f]{64}$")


class ContractError(RuntimeError):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def inspect_image(path: Path) -> str:
    try:
        with Image.open(path) as image:
            image.verify()
            image_format = image.format
    except (OSError, UnidentifiedImageError) as exc:
        raise ContractError("blocked_reference_materialization", f"reference is not a decodable image: {path}: {exc}") from exc
    if image_format not in {"PNG", "JPEG", "WEBP"}:
        raise ContractError("blocked_reference_materialization", f"unsupported reference image format {image_format}: {path}")
    return image_format


def write_json_atomic(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    os.replace(temporary, path)


def parse_source(raw: str) -> tuple[str, str, Path]:
    parts = raw.split(":", 2)
    if len(parts) != 3:
        raise ContractError("blocked_reference_materialization", "--source must use REFERENCE_ID:ROLE:PATH")
    reference_id, role, source_path = parts
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{1,63}", reference_id):
        raise ContractError("blocked_reference_materialization", f"invalid reference id: {reference_id}")
    if role not in ROLES:
        raise ContractError("blocked_reference_materialization", f"invalid reference role: {role}")
    return reference_id, role, Path(source_path)


def freeze_bundle(
    *,
    run_id: str,
    view_id: str,
    attempt_id: str,
    output: Path,
    sources: list[tuple[str, str, Path]],
    rights_state: str,
    source_evidence_sha256: str | None,
    moment_canon_sha256: str | None,
    bridge_origins: dict[str, dict[str, str]],
    allow_empty_text_anchor: bool = False,
) -> dict[str, Any]:
    unsupported_roles = sorted({role for _reference_id, role, _path in sources if role not in ROLES})
    if unsupported_roles:
        raise ContractError(
            "blocked_reference_materialization",
            f"unsupported reference roles in v1: {unsupported_roles}; generated view bridges are not accepted as source authority",
        )
    if bridge_origins:
        raise ContractError(
            "blocked_reference_materialization",
            "generated view bridges are unsupported in v1 because durable origin-package lineage is not available",
        )
    if not 0 <= len(sources) <= 5 or (not sources and not allow_empty_text_anchor):
        raise ContractError("blocked_reference_materialization", "a bundle requires one to five references, except an explicit empty text-anchor attempt")
    if not sources and (view_id != "V00" or attempt_id == "PLAN"):
        raise ContractError("blocked_reference_materialization", "empty text-anchor bundles are limited to a generated V00 attempt")
    if sources and sources[0][1] != "moment_anchor":
        raise ContractError("blocked_reference_materialization", "the first reference must be moment_anchor")
    if rights_state not in RIGHTS_STATES:
        raise ContractError("blocked_reference_materialization", f"invalid rights_state: {rights_state}")
    for label, value in (("source_evidence_sha256", source_evidence_sha256), ("moment_canon_sha256", moment_canon_sha256)):
        if value is not None and not SHA_RE.fullmatch(value):
            raise ContractError("blocked_reference_materialization", f"invalid {label}")

    output = output.resolve()
    reference_root = output.parent / "references"
    if reference_root.exists() and reference_root.is_symlink():
        raise ContractError("blocked_reference_materialization", "destination references directory cannot be a symlink")
    reference_root.mkdir(parents=True, exist_ok=True)
    existing = list(reference_root.iterdir())
    if existing:
        raise ContractError("blocked_reference_destination_conflict", f"destination references directory is not empty: {reference_root}")

    reference_ids = [reference_id for reference_id, _role, _path in sources]
    if len(set(reference_ids)) != len(reference_ids):
        raise ContractError("blocked_reference_materialization", "reference IDs must be unique")
    resolved_sources: list[Path] = []
    source_formats: list[str] = []
    for _reference_id, _role, source in sources:
        if source.is_symlink():
            raise ContractError("blocked_reference_materialization", f"reference source cannot be a symlink: {source}")
        resolved = source.resolve()
        if not resolved.is_file():
            raise ContractError("blocked_reference_materialization", f"reference source missing: {source}")
        if resolved == reference_root or reference_root in resolved.parents:
            raise ContractError("blocked_reference_materialization", "reference source must remain outside destination")
        resolved_sources.append(resolved)
        source_formats.append(inspect_image(resolved))
    normalized = [os.path.normcase(str(path)) for path in resolved_sources]
    if len(set(normalized)) != len(normalized):
        raise ContractError("blocked_reference_materialization", "reference source paths must be unique")

    planned = [
        {
            "index": index,
            "reference_id": reference_id,
            "role": role,
            "source_path": str(source),
            "rights_state": rights_state,
            "bridge_origin": None,
        }
        for index, ((reference_id, role, _), source) in enumerate(zip(sources, resolved_sources), 1)
    ]
    reference_plan_sha256 = sha256_bytes(
        canonical_json(
            planned
            if planned
            else {
                "schema_version": "frozen_moment_reference_bundle.v1",
                "ordered_references": [],
                "input_mode": "text_anchor",
            }
        )
    )
    entries: list[dict[str, Any]] = []
    for index, (((reference_id, role, _), source), image_format) in enumerate(zip(zip(sources, resolved_sources), source_formats), 1):
        suffix = source.suffix.lower() or ".bin"
        alias = f"{index:02d}-{reference_id.lower()}"
        frozen = reference_root / f"{alias}{suffix}"
        shutil.copyfile(source, frozen)
        if sha256_file(source) != sha256_file(frozen):
            raise ContractError("blocked_reference_bytes_changed", f"copy mismatch: {reference_id}")
        if inspect_image(frozen) != image_format:
            raise ContractError("blocked_reference_bytes_changed", f"decoded image format changed: {reference_id}")
        include_scope, exclude_scope = DEFAULT_SCOPES[role]
        entries.append(
            {
                "index": index,
                "reference_id": reference_id,
                "alias": alias,
                "role": role,
                "authority_class": "source_anchor",
                "scope_include": include_scope,
                "scope_exclude": exclude_scope,
                "source_record_id": reference_id,
                "source_path": str(source),
                "frozen_path": str(frozen.resolve()),
                "size_bytes": frozen.stat().st_size,
                "sha256": sha256_file(frozen),
                "media_format": image_format,
                "rights_state": rights_state,
                "origin_view_id": None,
                "origin_attempt_id": None,
                "origin_inspection_sha256": None,
                "origin_inspection_path": None,
            }
        )
    ordered_bundle_sha256 = sha256_bytes(canonical_json(entries))
    manifest = {
        "schema_version": "frozen_moment_reference_bundle.v1",
        "run_id": run_id,
        "view_id": view_id,
        "attempt_id": attempt_id,
        "source_evidence_sha256": source_evidence_sha256,
        "moment_canon_sha256": moment_canon_sha256,
        "reference_plan_sha256": reference_plan_sha256,
        "ordered_references": entries,
        "ordered_bundle_sha256": ordered_bundle_sha256,
        "immutability_contract": "run_scoped_exact_bytes_utf8_manifest_lf",
        "provider_reference_count": len(entries),
    }
    write_json_atomic(output, manifest)
    return manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--view-id", required=True)
    parser.add_argument("--attempt-id", default="PLAN")
    parser.add_argument("--source", action="append", default=[], metavar="REFERENCE_ID:ROLE:PATH")
    parser.add_argument("--allow-empty-text-anchor", action="store_true")
    parser.add_argument("--rights-state", default="user_supplied", choices=sorted(RIGHTS_STATES))
    parser.add_argument("--source-evidence-sha256")
    parser.add_argument("--moment-canon-sha256")
    parser.add_argument("--output", required=True, type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        sources = [parse_source(raw) for raw in args.source]
        manifest = freeze_bundle(
            run_id=args.run_id,
            view_id=args.view_id.upper(),
            attempt_id=args.attempt_id,
            output=args.output,
            sources=sources,
            rights_state=args.rights_state,
            source_evidence_sha256=args.source_evidence_sha256,
            moment_canon_sha256=args.moment_canon_sha256,
            bridge_origins={},
            allow_empty_text_anchor=args.allow_empty_text_anchor,
        )
    except (ContractError, OSError) as exc:
        code = exc.code if isinstance(exc, ContractError) else "blocked_reference_filesystem"
        print(json.dumps({"ok": False, "error_code": code, "detail": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps({"ok": True, "output": str(args.output.resolve()), "ordered_bundle_sha256": manifest["ordered_bundle_sha256"]}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
