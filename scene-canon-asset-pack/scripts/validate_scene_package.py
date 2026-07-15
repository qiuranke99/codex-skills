#!/usr/bin/env python3
"""Validate Scene Canon v2 state or strict six-asset delivery."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from itertools import combinations
from pathlib import Path
from typing import Any, Iterable

import resolve_worker_image as worker_resolver
from build_review_board import compose_review_board

try:
    from PIL import Image
except ImportError:  # delivery fails closed below
    Image = None


SKILL_DIR = Path(__file__).resolve().parents[1]
REFERENCES_DIR = SKILL_DIR / "references"
MACHINE_ASSET_IDS = ["CDM_001", "SRM_001", "COV_001", "COV_002", "COV_003", "SCL_001"]
ROLE_BY_ASSET = {
    "CDM_001": "source_aligned_diagnostic",
    "SRM_001": "elevated_spatial_relation",
    "COV_001": "left_adjacent_continuity",
    "COV_002": "right_adjacent_continuity",
    "COV_003": "motion_reveal",
    "SCL_001": "scale_landmark_depth",
}
TYPE_BY_ASSET = {
    "CDM_001": "canonical_diagnostic_master",
    "SRM_001": "spatial_relational_master",
    "COV_001": "coverage_plate",
    "COV_002": "coverage_plate",
    "COV_003": "coverage_plate",
    "SCL_001": "scale_landmark",
}
DEPENDENCIES = {
    "CDM_001": [],
    "SRM_001": ["CDM_001"],
    "COV_001": ["CDM_001", "SRM_001"],
    "COV_002": ["CDM_001", "SRM_001"],
    "COV_003": ["CDM_001", "SRM_001", "COV_001", "COV_002"],
    "SCL_001": ["CDM_001", "SRM_001", "COV_003"],
}
STAGES = {"CDM_001": 1, "SRM_001": 2, "COV_001": 3, "COV_002": 3, "COV_003": 4, "SCL_001": 5}
PLACEHOLDER = re.compile(r"\b(?:todo|tbd|placeholder|fixture evidence|replace me|lorem ipsum)\b|<[^>]+>", re.I)
TRANSLATIONAL = {"truck", "crane", "orbit", "approach", "departure"}


def read_json(path: Path) -> Any:
    def reject_non_finite(value: str) -> Any:
        raise ValueError(f"non-finite JSON number is forbidden: {value}")

    return json.loads(path.read_text(encoding="utf-8"), parse_constant=reject_non_finite)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def canonical_json_hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256_text(payload)


def resolve_ref(schema: dict[str, Any], root: dict[str, Any]) -> dict[str, Any]:
    ref = schema.get("$ref")
    if not ref:
        return schema
    if not ref.startswith("#/"):
        raise ValueError(f"unsupported external schema reference: {ref}")
    current: Any = root
    for token in ref[2:].split("/"):
        current = current[token.replace("~1", "/").replace("~0", "~")]
    return current


def type_matches(value: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "null":
        return value is None
    return True


def validate_schema_value(value: Any, schema: dict[str, Any], root: dict[str, Any], path: str = "$") -> list[str]:
    errors: list[str] = []
    schema = resolve_ref(schema, root)
    expected = schema.get("type")
    if expected:
        options = expected if isinstance(expected, list) else [expected]
        if not any(type_matches(value, option) for option in options):
            return [f"{path}: expected type {options}, got {type(value).__name__}"]
    if "const" in schema and value != schema["const"]:
        errors.append(f"{path}: expected constant {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: value {value!r} is not in enum")
    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                errors.append(f"{path}: missing required key {key!r}")
        properties = schema.get("properties", {})
        additional = schema.get("additionalProperties")
        if additional is False:
            for key in sorted(set(value) - set(properties)):
                errors.append(f"{path}: unexpected key {key!r}")
        for key, child in value.items():
            if key in properties:
                errors.extend(validate_schema_value(child, properties[key], root, f"{path}.{key}"))
            elif isinstance(additional, dict):
                errors.extend(validate_schema_value(child, additional, root, f"{path}.{key}"))
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            errors.append(f"{path}: requires at least {schema['minItems']} items")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            errors.append(f"{path}: allows at most {schema['maxItems']} items")
        if schema.get("uniqueItems"):
            normalized = [json.dumps(item, sort_keys=True, ensure_ascii=False) for item in value]
            if len(normalized) != len(set(normalized)):
                errors.append(f"{path}: items must be unique")
        if schema.get("items"):
            for index, child in enumerate(value):
                errors.extend(validate_schema_value(child, schema["items"], root, f"{path}[{index}]"))
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            errors.append(f"{path}: string is shorter than {schema['minLength']}")
        if schema.get("pattern") and not re.search(schema["pattern"], value):
            errors.append(f"{path}: string does not match pattern {schema['pattern']!r}")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if isinstance(value, float) and not math.isfinite(value):
            errors.append(f"{path}: number must be finite")
            return errors
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{path}: value is below minimum {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            errors.append(f"{path}: value is above maximum {schema['maximum']}")
    return errors


def local_path(root: Path, value: str, label: str, errors: list[str]) -> Path | None:
    try:
        path = (root / value).resolve()
        path.relative_to(root)
    except (OSError, ValueError):
        errors.append(f"{label}: path escapes package root: {value!r}")
        return None
    return path


def require_local_file(root: Path, value: str, label: str, errors: list[str]) -> Path | None:
    path = local_path(root, value, label, errors)
    if path is not None and not path.is_file():
        errors.append(f"{label}: missing file {value}")
        return None
    return path


def dimensions(path: Path) -> tuple[int, int]:
    if Image is None:
        raise RuntimeError("Pillow is required for strict image verification")
    with Image.open(path) as image:
        image.verify()
    with Image.open(path) as image:
        return image.size


def image_hashes(path: Path) -> tuple[int, int, int]:
    if Image is None:
        raise RuntimeError("Pillow is required for perceptual duplicate detection")
    values: list[int] = []
    with Image.open(path) as source:
        image = source.convert("L")
        for fraction in (1.0, 0.9, 0.8):
            if fraction < 1.0:
                width, height = image.size
                left = int(width * (1.0 - fraction) / 2.0)
                top = int(height * (1.0 - fraction) / 2.0)
                current = image.crop((left, top, width - left, height - top))
            else:
                current = image
            current = current.resize((9, 8), Image.Resampling.LANCZOS)
            pixels = list(current.getdata())
            bits = 0
            for row in range(8):
                for column in range(8):
                    left_value = pixels[row * 9 + column]
                    right_value = pixels[row * 9 + column + 1]
                    bits = (bits << 1) | int(right_value > left_value)
            values.append(bits)
    return tuple(values)  # type: ignore[return-value]


def decoded_pixel_sha256(path: Path) -> str:
    if Image is None:
        raise RuntimeError("Pillow is required for decoded-pixel duplicate detection")
    with Image.open(path) as source:
        image = source.convert("RGB")
        payload = f"{image.width}x{image.height}:RGB:".encode("ascii") + image.tobytes()
    return sha256_bytes(payload)


def similarity_thumbnail(path: Path) -> bytes:
    if Image is None:
        raise RuntimeError("Pillow is required for visual duplicate detection")
    with Image.open(path) as source:
        return source.convert("RGB").resize((64, 36), Image.Resampling.LANCZOS).tobytes()


def hamming(a: int, b: int) -> int:
    return (a ^ b).bit_count()


def pose_tuple(node: dict[str, Any]) -> tuple[Any, ...]:
    pose = node["camera_pose"]
    return (
        round(float(pose["x"]), 4), round(float(pose["y"]), 4), round(float(pose["z"]), 4),
        round(float(pose["yaw_degrees"]), 3), round(float(pose["pitch_degrees"]), 3), round(float(pose["roll_degrees"]), 3),
        pose["lens_fov_class"], pose["distance_framing_class"],
    )


def flatten_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, child in value.items():
            yield str(key)
            yield from flatten_strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from flatten_strings(child)


def values_for_key(value: Any, target: str) -> Iterable[Any]:
    if isinstance(value, dict):
        for key, child in value.items():
            if key == target:
                yield child
            yield from values_for_key(child, target)
    elif isinstance(value, list):
        for child in value:
            yield from values_for_key(child, target)


def meaningful(text: str, minimum: int = 80) -> bool:
    return len(text.strip()) >= minimum and not PLACEHOLDER.search(text)


def validate_graph(canon: dict[str, Any], errors: list[str]) -> tuple[dict[str, Any], dict[str, Any]]:
    graph = canon["coverage_graph"]
    envelope = canon["supported_camera_motion_envelope"]
    if graph["profile_id"] != "scene_motion_six.v1" or envelope["profile_id"] != "scene_motion_six.v1":
        errors.append("motion envelope and coverage graph must use scene_motion_six.v1")
    if graph["graph_status"] != "verified":
        errors.append("delivery coverage graph must be verified")
    if graph["required_asset_ids"] != MACHINE_ASSET_IDS:
        errors.append("coverage graph required_asset_ids must equal the ordered six-asset profile")
    nodes = graph["nodes"]
    edges = graph["edges"]
    if len(nodes) != 6:
        errors.append("coverage graph must contain exactly six mandatory nodes")
    if len(edges) < 6:
        errors.append("coverage graph requires at least six continuity edges")
    node_ids = [node["node_id"] for node in nodes]
    node_asset_ids = [node["asset_id"] for node in nodes]
    roles = [node["role"] for node in nodes]
    if len(node_ids) != len(set(node_ids)):
        errors.append("coverage graph node IDs must be unique")
    if node_asset_ids != MACHINE_ASSET_IDS:
        errors.append("coverage graph nodes must follow the ordered six-asset profile")
    if set(roles) != set(ROLE_BY_ASSET.values()) or len(roles) != len(set(roles)):
        errors.append("coverage graph mandatory roles must be unique and complete")
    node_by_id = {node["node_id"]: node for node in nodes}
    node_by_asset = {node["asset_id"]: node for node in nodes}
    landmark_ids = {item["landmark_id"] for item in canon["landmark_list"]}
    evidence_ids = {
        item["element_id"]
        for item in canon["source_locked_elements"] + canon["source_corroborated_elements"]
    }
    completion_by_id = {item["element_id"]: item for item in canon["canonical_completion_elements"]}
    for asset_id, role in ROLE_BY_ASSET.items():
        node = node_by_asset.get(asset_id)
        if node and node["role"] != role:
            errors.append(f"{asset_id}: coverage role mismatch")
    tuples = [pose_tuple(node) for node in nodes]
    if len(tuples) != len(set(tuples)):
        errors.append("duplicate camera tuple across mandatory coverage nodes")
    directions = {(item[3], item[4]) for item in tuples}
    if len(directions) < 4:
        errors.append("coverage graph has insufficient camera direction diversity")
    azimuth = envelope["azimuth_degrees"]
    elevation = envelope["elevation_degrees"]
    for node in nodes:
        pose = node["camera_pose"]
        if not azimuth["min"] <= pose["yaw_degrees"] <= azimuth["max"]:
            errors.append(f"{node['node_id']}: yaw lies outside motion envelope")
        if not elevation["min"] <= pose["pitch_degrees"] <= elevation["max"]:
            errors.append(f"{node['node_id']}: pitch lies outside motion envelope")
        bounds = envelope["translation_bounds_normalized"]
        for axis in ("x", "y", "z"):
            if not bounds[axis]["min"] <= pose[axis] <= bounds[axis]["max"]:
                errors.append(f"{node['node_id']}: {axis} position lies outside motion envelope")
        if not set(node["visible_landmark_ids"]).issubset(landmark_ids):
            errors.append(f"{node['node_id']}: visible landmark reference is unresolved")
        if not set(node["source_evidence_ids"]).issubset(evidence_ids):
            errors.append(f"{node['node_id']}: source evidence reference is unresolved")
        for completion_id in node["canonical_completion_ids"]:
            completion = completion_by_id.get(completion_id)
            if completion is None or completion.get("status") != "approved":
                errors.append(f"{node['node_id']}: canonical completion reference is unresolved or unapproved")
    if all(asset in node_by_asset for asset in MACHINE_ASSET_IDS):
        cdm = node_by_asset["CDM_001"]["camera_pose"]
        if node_by_asset["COV_001"]["camera_pose"]["x"] >= cdm["x"]:
            errors.append("left-adjacent node must lie left of CDM")
        if node_by_asset["COV_002"]["camera_pose"]["x"] <= cdm["x"]:
            errors.append("right-adjacent node must lie right of CDM")
        if node_by_asset["SRM_001"]["camera_pose"]["y"] <= cdm["y"]:
            errors.append("spatial-relational node must be elevated above CDM")
        reveal = node_by_asset["COV_003"]["camera_pose"]
        if reveal["y"] == cdm["y"] and reveal["z"] == cdm["z"]:
            errors.append("motion-reveal node must add a vertical or depth baseline")
        if node_by_asset["SCL_001"]["camera_pose"]["z"] == cdm["z"]:
            errors.append("scale-landmark node must add a depth baseline")
    edge_ids = [edge["edge_id"] for edge in edges]
    if len(edge_ids) != len(set(edge_ids)):
        errors.append("coverage edge IDs must be unique")
    edge_by_id = {edge["edge_id"]: edge for edge in edges}
    expected_adjacency: dict[str, set[str]] = {node_id: set() for node_id in node_by_id}
    for edge in edges:
        start = node_by_id.get(edge["from_node_id"])
        end = node_by_id.get(edge["to_node_id"])
        if start is None or end is None:
            errors.append(f"{edge['edge_id']}: edge endpoint is missing")
            continue
        expected_adjacency[start["node_id"]].add(end["node_id"])
        expected_adjacency[end["node_id"]].add(start["node_id"])
        if end["node_id"] not in start["adjacent_node_ids"] or start["node_id"] not in end["adjacent_node_ids"]:
            errors.append(f"{edge['edge_id']}: adjacency must be bidirectional in both nodes")
        if not (set(start["visible_landmark_ids"]) & set(end["visible_landmark_ids"])):
            errors.append(f"{edge['edge_id']}: adjacent nodes share no visible landmark")
        shared_invariants = set(edge["overlap_invariant_ids"])
        if not shared_invariants.issubset(set(start["overlap_invariant_ids"]) & set(end["overlap_invariant_ids"])):
            errors.append(f"{edge['edge_id']}: overlap invariants are not shared by both nodes")
        if edge["movement_type"] in TRANSLATIONAL:
            if edge["translation_baseline_normalized"] <= 0:
                errors.append(f"{edge['edge_id']}: translated motion requires non-zero baseline")
            if not edge["parallax_expected"] or edge["parallax_evidence_status"] != "verified":
                errors.append(f"{edge['edge_id']}: translated motion requires verified parallax")
        elif edge["parallax_expected"] and edge["parallax_evidence_status"] != "verified":
            errors.append(f"{edge['edge_id']}: expected parallax is not verified")
    included_regions = set(canon["minimum_complete_scene_boundary"]["included_regions"])
    for node_id, expected in expected_adjacency.items():
        if set(node_by_id[node_id]["adjacent_node_ids"]) != expected:
            errors.append(f"{node_id}: adjacency list must exactly match graph edges")
    for edge in edges:
        if not set(edge["reveal_order_region_ids"]).issubset(included_regions):
            errors.append(f"{edge['edge_id']}: reveal order lies outside minimum-complete boundary")
    for node in nodes:
        if not set(node["revealed_region_ids"]).issubset(included_regions):
            errors.append(f"{node['node_id']}: revealed region lies outside minimum-complete boundary")
    path_ids = [path["path_id"] for path in graph["paths"]]
    if len(path_ids) != len(set(path_ids)):
        errors.append("coverage path IDs must be unique")
    if set(envelope["supported_path_ids"]) != set(path_ids):
        errors.append("motion envelope supported_path_ids must match coverage paths")
    if not set(envelope["included_reveal_region_ids"]).issubset(included_regions):
        errors.append("motion envelope reveal region lies outside minimum-complete boundary")
    edge_membership: dict[str, set[str]] = {edge_id: set() for edge_id in edge_by_id}
    path_node_membership: set[str] = set()
    for path in graph["paths"]:
        if any(node_id not in node_by_id for node_id in path["node_ids"]):
            errors.append(f"{path['path_id']}: path references a missing node")
        if any(edge_id not in edge_by_id for edge_id in path["edge_ids"]):
            errors.append(f"{path['path_id']}: path references a missing edge")
        for edge_id in path["edge_ids"]:
            if edge_id in edge_by_id and path["path_id"] not in edge_by_id[edge_id]["path_ids"]:
                errors.append(f"{path['path_id']}: edge does not declare path membership")
            if edge_id in edge_membership:
                edge_membership[edge_id].add(path["path_id"])
        path_node_membership.update(path["node_ids"])
        path_nodes = path["node_ids"]
        path_edges = path["edge_ids"]
        is_closed = len(path_edges) == len(path_nodes)
        expected_edge_count = len(path_nodes) if is_closed else max(0, len(path_nodes) - 1)
        if len(path_edges) != expected_edge_count:
            errors.append(f"{path['path_id']}: path node/edge counts do not form an executable sequence")
        elif path_nodes:
            destinations = path_nodes[1:] + ([path_nodes[0]] if is_closed else [])
            for edge_id, left, right in zip(path_edges, path_nodes, destinations):
                edge = edge_by_id.get(edge_id)
                if edge is not None and (edge["from_node_id"], edge["to_node_id"]) != (left, right):
                    errors.append(f"{path['path_id']}: edge {edge_id} does not execute {left}->{right}")
            executable_movements = {
                edge_by_id[edge_id]["movement_type"]
                for edge_id in path_edges
                if edge_id in edge_by_id
            }
            if set(path["supported_movement_types"]) != executable_movements:
                errors.append(f"{path['path_id']}: declared movements do not match its executable edges")
    for edge_id, edge in edge_by_id.items():
        if set(edge["path_ids"]) != edge_membership[edge_id]:
            errors.append(f"{edge_id}: edge/path membership must be exact and bidirectional")
    if path_node_membership != set(node_by_id):
        errors.append("every coverage node must belong to at least one executable path")
    if not graph["loops"]:
        errors.append("coverage graph requires loop closure")
    for loop in graph["loops"]:
        if loop["convergence_status"] != "verified":
            errors.append(f"{loop['loop_id']}: loop closure is not verified")
        if any(node_id not in node_by_id for node_id in loop["node_ids"]):
            errors.append(f"{loop['loop_id']}: loop references a missing node")
        if any(edge_id not in edge_by_id for edge_id in loop["edge_ids"]):
            errors.append(f"{loop['loop_id']}: loop references a missing edge")
        loop_nodes = loop["node_ids"]
        loop_edges = loop["edge_ids"]
        if len(loop_nodes) != len(set(loop_nodes)) or len(loop_edges) != len(set(loop_edges)) or len(loop_nodes) != len(loop_edges):
            errors.append(f"{loop['loop_id']}: loop nodes/edges must be unique and one-to-one")
        for edge_id, left, right in zip(loop_edges, loop_nodes, loop_nodes[1:] + loop_nodes[:1]):
            edge = edge_by_id.get(edge_id)
            if edge is None or (edge["from_node_id"], edge["to_node_id"]) != (left, right):
                errors.append(f"{loop['loop_id']}: loop edge {edge_id} does not execute {left}->{right}")
        closure = set(loop["closure_landmark_ids"])
        if not closure.issubset(landmark_ids) or any(not closure.issubset(set(node_by_id[node_id]["visible_landmark_ids"])) for node_id in loop_nodes if node_id in node_by_id):
            errors.append(f"{loop['loop_id']}: closure landmarks must exist and remain visible at every loop node")
    edge_movements = {edge["movement_type"] for edge in edges}
    for movement in envelope["supported_movement_types"]:
        if movement != "locked_off" and movement not in edge_movements:
            errors.append(f"supported motion {movement!r} has no executable coverage edge")
    if not canon["unsupported_camera_motion"]:
        errors.append("unsupported_camera_motion must state the package boundary")
    if "orbit" in envelope["supported_movement_types"] and azimuth["max"] - azimuth["min"] >= 360:
        if envelope["backside_truth_status"] == "outside_envelope":
            errors.append("360-degree orbit cannot exclude backside truth")
    declared_reveals = set().union(*(set(node["revealed_region_ids"]) for node in nodes), *(set(edge["reveal_order_region_ids"]) for edge in edges))
    if not set(envelope["included_reveal_region_ids"]).issubset(declared_reveals):
        errors.append("motion envelope reveal regions are not evidenced by coverage nodes or edges")
    return node_by_id, node_by_asset


def validate_reference_manifest(
    root: Path,
    path: Path,
    result: dict[str, Any],
    asset_id: str,
    primary_reference: str,
    reference_plan: list[dict[str, Any]],
    expected_source_path: Path,
    expected_dependency_paths: dict[str, Path],
    errors: list[str],
) -> None:
    label = asset_id
    path = path.resolve()
    if not path.is_relative_to(root):
        errors.append(f"{label}: reference manifest escapes the package root")
        return
    if not path.is_file():
        errors.append(f"{label}: reference manifest is missing")
        return
    if sha256_file(path) != result.get("reference_manifest_sha256"):
        errors.append(f"{label}: reference manifest hash mismatch")
        return
    try:
        manifest = read_json(path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        errors.append(f"{label}: invalid reference manifest: {exc}")
        return
    entries = manifest.get("ordered_references")
    expected_manifest_keys = {"schema_version", "asset_id", "source_reference_id", "ordered_references", "ordered_bundle_sha256"}
    if set(manifest) != expected_manifest_keys or manifest.get("schema_version") != "scene_canon_reference_bundle.v1" or not isinstance(entries, list):
        errors.append(f"{label}: unsupported ordered reference manifest")
        return
    if manifest.get("asset_id") != asset_id or manifest.get("source_reference_id") != primary_reference:
        errors.append(f"{label}: reference manifest targets the wrong asset or primary source")
    expected_parent = root / "10_runtime" / asset_id.lower()
    if path.parent != expected_parent or path.name != "reference-manifest.json":
        errors.append(f"{label}: reference manifest must use the asset-scoped runtime directory")
    if not 1 <= len(entries) <= 5 or result.get("reference_count") != len(entries):
        errors.append(f"{label}: worker must bind one to five ordered references")
    actual = canonical_json_hash(entries)
    if manifest.get("ordered_bundle_sha256") != actual or result.get("ordered_reference_bundle_sha256") != actual:
        errors.append(f"{label}: ordered reference bundle hash mismatch")
    for index, entry in enumerate(entries, 1):
        expected_entry_keys = {"index", "alias", "kind", "source_reference_id", "asset_id", "source_path", "frozen_path", "size_bytes", "sha256"}
        if set(entry) != expected_entry_keys:
            errors.append(f"{label}: reference entry fields are incomplete or unexpected")
        if entry.get("index") != index:
            errors.append(f"{label}: reference indices are not contiguous")
        frozen = Path(str(entry.get("frozen_path", "")))
        try:
            frozen = frozen.resolve()
        except OSError:
            errors.append(f"{label}: frozen reference path is invalid")
            continue
        expected_reference_root = path.parent / "references"
        if not frozen.is_relative_to(expected_reference_root):
            errors.append(f"{label}: frozen reference is outside its asset-scoped references directory")
        elif not frozen.is_relative_to(root):
            errors.append(f"{label}: frozen reference escapes the package root")
        elif not frozen.is_file() or sha256_file(frozen) != entry.get("sha256") or frozen.stat().st_size != entry.get("size_bytes"):
            errors.append(f"{label}: frozen reference bytes changed")
        try:
            source_path = Path(str(entry.get("source_path", ""))).resolve()
        except OSError:
            errors.append(f"{label}: reference source path is invalid")
            continue
        expected_source = expected_source_path if entry.get("kind") == "source_reference" else expected_dependency_paths.get(str(entry.get("asset_id")))
        if expected_source is None or source_path != expected_source.resolve():
            errors.append(f"{label}: reference source path does not bind the packaged source/predecessor")
    source_entries = [entry for entry in entries if entry.get("kind") == "source_reference"]
    if len(source_entries) != 1 or source_entries[0].get("index") != 1:
        errors.append(f"{label}: frozen original scene source must be reference 1")
    manifest_plan = [
        {
            "index": entry.get("index"),
            "alias": entry.get("alias"),
            "kind": entry.get("kind"),
            "source_reference_id": entry.get("source_reference_id"),
            "predecessor_asset_id": entry.get("asset_id"),
        }
        for entry in entries
    ]
    if manifest_plan != reference_plan:
        errors.append(f"{label}: frozen reference order does not exactly match the published prompt plan")
    listed_paths = {Path(str(entry["frozen_path"])).resolve() for entry in entries}
    reference_root = path.parent / "references"
    actual_paths = {item.resolve() for item in reference_root.iterdir() if item.is_file()} if reference_root.is_dir() else set()
    if not reference_root.is_dir() or any(item.is_dir() for item in reference_root.iterdir()) or actual_paths != listed_paths:
        errors.append(f"{label}: asset-scoped references contain missing or unlisted files")


def validate_prompt_publication(
    root: Path,
    manifest: dict[str, Any],
    prompts: list[dict[str, Any]],
    prompt_doc: str,
    errors: list[str],
) -> dict[str, Any] | None:
    receipt_path = require_local_file(root, manifest["prompt_publication_receipt_path"], "prompt publication receipt", errors)
    if receipt_path is None:
        return None
    if sha256_file(receipt_path) != manifest["prompt_publication_receipt_sha256"]:
        errors.append("prompt publication receipt hash mismatch")
        return None
    try:
        receipt = read_json(receipt_path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        errors.append(f"prompt publication receipt is invalid: {exc}")
        return None
    required = {
        "schema_version", "origin", "parent_thread_id", "parent_rollout_path", "parent_rollout_sha256",
        "publication_event_id", "publication_event_index", "publication_elapsed_ms", "prompt_document_sha256",
        "published_prompt_ids", "published_prompt_sha256", "first_worker_spawn_event_index", "first_worker_spawn_elapsed_ms",
    }
    if not required.issubset(receipt):
        errors.append("prompt publication receipt is missing runtime fields")
        return receipt
    if receipt["schema_version"] != "scene_prompt_publication_receipt.v1":
        errors.append("unsupported prompt publication receipt schema")
    if not isinstance(receipt["parent_thread_id"], str) or not receipt["parent_thread_id"]:
        errors.append("prompt publication receipt parent thread ID is missing")
    if receipt["origin"] != manifest["runtime_evidence_origin"]:
        errors.append("prompt publication receipt origin mismatch")
    if receipt["prompt_document_sha256"] != sha256_text(prompt_doc):
        errors.append("publication receipt does not bind generation prompt document")
    expected_ids = [prompt["prompt_id"] for prompt in prompts]
    expected_hashes = [prompt["prompt_sha256"] for prompt in prompts]
    if receipt["published_prompt_ids"] != expected_ids or receipt["published_prompt_sha256"] != expected_hashes:
        errors.append("publication receipt does not bind all six prompts in order")
    if (
        not isinstance(receipt["publication_elapsed_ms"], int)
        or not isinstance(receipt["first_worker_spawn_elapsed_ms"], int)
        or receipt["publication_elapsed_ms"] < 0
        or receipt["first_worker_spawn_elapsed_ms"] < 0
        or receipt["publication_elapsed_ms"] >= receipt["first_worker_spawn_elapsed_ms"]
    ):
        errors.append("all six prompts must be public before first worker spawn")
    rollout = Path(str(receipt["parent_rollout_path"]))
    if not rollout.is_file() or sha256_file(rollout) != receipt["parent_rollout_sha256"]:
        errors.append("prompt publication parent rollout is missing or hash-mismatched")
        return receipt
    found_events: list[tuple[int, Any]] = []
    try:
        rollout_events = []
        for line in rollout.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            event = json.loads(line)
            index = len(rollout_events)
            rollout_events.append(event)
            if receipt["publication_event_id"] in set(flatten_strings(event)):
                found_events.append((index, event))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        errors.append(f"prompt publication parent rollout is unreadable: {exc}")
        return receipt
    if not rollout_events or rollout_events[0].get("type") != "session_meta" or rollout_events[0].get("payload", {}).get("id") != receipt["parent_thread_id"]:
        errors.append("prompt publication parent thread does not match parent rollout session")
    if len(found_events) != 1:
        errors.append("prompt publication event must appear exactly once in parent rollout")
    else:
        event_index, found_event = found_events[0]
        if not isinstance(receipt["publication_event_index"], int) or receipt["publication_event_index"] < 0 or receipt["publication_event_index"] != event_index:
            errors.append("prompt publication event index does not match parent rollout")
        if receipt["publication_elapsed_ms"] not in set(values_for_key(found_event, "elapsed_ms")):
            errors.append("prompt publication elapsed time is not bound by the publication event")
        if not isinstance(receipt["first_worker_spawn_event_index"], int) or receipt["first_worker_spawn_event_index"] <= event_index:
            errors.append("prompt publication event must precede the first worker spawn event")
        event_text = "\n".join(flatten_strings(found_event))
        for prompt in prompts:
            if prompt["prompt_id"] not in event_text or prompt["prompt_sha256"] not in event_text or prompt["prompt_body"] not in event_text:
                errors.append(f"{prompt['prompt_id']}: complete prompt body/hash was not published in the bound event")
    return receipt


def validate_live_worker_lineage(
    result: dict[str, Any],
    prompt: dict[str, Any],
    reference_path: Path,
    errors: list[str],
    label: str,
) -> None:
    required = {
        "worker_task_name", "worker_turn_id", "worker_rollout_path", "parent_rollout_path",
        "parent_spawn_call_id", "parent_spawn_turn_id", "task_delivery_ciphertext_sha256",
        "worker_saved_path", "reference_mode",
    }
    missing = sorted(required - set(result))
    if missing:
        errors.append(f"{label}: live worker result missing audited provenance fields: {', '.join(missing)}")
        return
    try:
        reference_manifest = read_json(reference_path)
        expected_references = [Path(item["frozen_path"]) for item in reference_manifest["ordered_references"]]
        worker_rollout = Path(str(result["worker_rollout_path"]))
        parent_rollout = Path(str(result["parent_rollout_path"]))
        worker_evidence = worker_resolver.validate_worker_rollout(
            worker_resolver.read_rollout(worker_rollout),
            thread_id=str(result.get("worker_thread_id", "")),
            agent_path=str(result.get("agent_path", "")),
            parent_thread_id=str(result.get("parent_thread_id", "")),
            worker_run_nonce=str(result.get("worker_run_nonce", "")),
            expected_prompt_bytes=prompt["prompt_body"].encode("utf-8"),
            expected_references=expected_references,
            allow_no_references=False,
        )
        spawn_evidence = worker_resolver.validate_parent_spawn_chain(
            worker_resolver.read_rollout(parent_rollout),
            parent_thread_id=str(result.get("parent_thread_id", "")),
            worker_thread_id=str(result.get("worker_thread_id", "")),
            agent_path=str(result.get("agent_path", "")),
            worker_run_nonce=str(result.get("worker_run_nonce", "")),
            delivery_ciphertext=worker_evidence["task_delivery_ciphertext"],
            not_before_ms=int(result.get("parent_spawn_activity_ms", -1)),
        )
    except (OSError, KeyError, TypeError, ValueError, worker_resolver.ContractError) as exc:
        errors.append(f"{label}: live worker lineage replay failed: {exc}")
        return
    expected_worker = {
        "worker_task_name": worker_evidence["worker_task_name"],
        "worker_turn_id": worker_evidence["worker_turn_id"],
        "image_generation_call_id": worker_evidence["call_id"],
        "tool_prompt_sha256": worker_evidence["tool_prompt_sha256"],
        "reference_mode": worker_evidence["reference_mode"],
    }
    for key, expected in expected_worker.items():
        if result.get(key) != expected:
            errors.append(f"{label}: live worker lineage field {key} does not match replayed evidence")
    if worker_resolver.normalized_path(Path(str(result["worker_saved_path"]))) != worker_resolver.normalized_path(Path(worker_evidence["saved_path"])):
        errors.append(f"{label}: live worker saved path does not match replayed evidence")
    for key in ("binding_mode", "parent_spawn_call_id", "parent_spawn_turn_id", "parent_spawn_event_index", "task_delivery_ciphertext_sha256"):
        if result.get(key) != spawn_evidence[key]:
            errors.append(f"{label}: live parent spawn field {key} does not match replayed evidence")
    if result.get("parent_spawn_activity_ms") != int(spawn_evidence["parent_spawn_activity_ms"]):
        errors.append(f"{label}: live parent spawn time does not match replayed evidence")


def validate_package(root: Path, mode: str = "delivery", fixture_mode: bool = False, through_asset: str | None = None) -> list[str]:
    root = root.resolve()
    errors: list[str] = []
    core_files = [
        "00_manifest/SCENE_CANON.md", "00_manifest/SCENE_CANON.json",
        "00_manifest/SOURCE_APPEARANCE_DECOMPOSITION.md", "00_manifest/SOURCE_APPEARANCE_DECOMPOSITION.json",
        "00_manifest/GENERATION_PROMPTS.md", "00_manifest/ASSET_INDEX.md",
        "00_manifest/ASSET_MANIFEST.json", "00_manifest/actual_image_dimensions.json",
    ]
    delivery_files = core_files + [
        "01_source_analysis/source_evidence_report.md", "01_source_analysis/conflict_report.md",
        "01_source_analysis/coverage_assessment.md", "08_4k_regeneration/4K_ASSET_REGENERATION_PROMPTS.md",
        "09_qa/QA_REPORT.md", "09_qa/failed_asset_log.md", "09_qa/look_contamination_report.md",
        "09_qa/coverage_graph_report.md", "09_qa/4k_prompt_mapping_report.md",
    ]
    for rel in delivery_files if mode == "delivery" else core_files:
        require_local_file(root, rel, "required package file", errors)
    if errors:
        return errors
    canon_path = root / "00_manifest/SCENE_CANON.json"
    appearance_path = root / "00_manifest/SOURCE_APPEARANCE_DECOMPOSITION.json"
    manifest_path = root / "00_manifest/ASSET_MANIFEST.json"
    dimensions_path = root / "00_manifest/actual_image_dimensions.json"
    prompt_doc_path = root / "00_manifest/GENERATION_PROMPTS.md"
    try:
        canon = read_json(canon_path)
        appearance = read_json(appearance_path)
        manifest = read_json(manifest_path)
        dimensions_index = read_json(dimensions_path)
        prompt_doc = prompt_doc_path.read_text(encoding="utf-8")
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return [f"package JSON read failed: {exc}"]
    for instance, schema_name, label in [
        (canon, "scene_canon.schema.json", "SCENE_CANON.json"),
        (appearance, "appearance_decomposition.schema.json", "SOURCE_APPEARANCE_DECOMPOSITION.json"),
        (manifest, "asset_manifest.schema.json", "ASSET_MANIFEST.json"),
    ]:
        schema = read_json(REFERENCES_DIR / schema_name)
        errors.extend(f"{label}: {item}" for item in validate_schema_value(instance, schema, schema))
    if errors:
        return errors
    if len({canon["scene_id"], appearance["scene_id"], manifest["scene_id"]}) != 1:
        errors.append("scene_id mismatch across canon, appearance, and manifest")
    canon_hash = sha256_file(canon_path)
    appearance_hash = sha256_file(appearance_path)
    completion_hash = canonical_json_hash(canon["canonical_completion_elements"])
    if manifest["canon_sha256"] != canon_hash or manifest["canon_revision"] != canon["canon_revision"]:
        errors.append("manifest does not bind the current Scene Canon")
    if manifest["appearance_sha256"] != appearance_hash or manifest["appearance_revision"] != appearance["appearance_revision"]:
        errors.append("manifest does not bind the current appearance decomposition")
    if manifest["completion_hash"] != completion_hash:
        errors.append("manifest completion hash is stale")
    if manifest["generation_prompt_document_sha256"] != sha256_text(prompt_doc):
        errors.append("generation prompt document hash mismatch")
    for rel in ("00_manifest/SCENE_CANON.md", "00_manifest/SOURCE_APPEARANCE_DECOMPOSITION.md", "00_manifest/ASSET_INDEX.md"):
        if not meaningful((root / rel).read_text(encoding="utf-8"), 80):
            errors.append(f"{rel}: core deliverable is placeholder or empty")
    if mode == "state":
        if manifest["package_status"] == "packaged":
            errors.append("packaged outputs must use strict delivery mode")
        return errors
    if mode == "stage":
        if through_asset not in MACHINE_ASSET_IDS:
            return errors + ["stage validation requires --through-asset from the six-asset profile"]
        if manifest["package_status"] not in {"generating", "repair_required", "graph_qa_pending", "four_k_mapping_failed"}:
            errors.append("stage validation requires an active non-packaged generation state")
        if manifest["task_finalization_status"] != "in_progress":
            errors.append("stage validation requires in-progress task finalization")
    else:
        if manifest["package_status"] != "packaged":
            errors.append("delivery validation requires package_status packaged")
        if manifest["task_finalization_status"] != "complete" or manifest["assistant_qa_status"] != "passed":
            errors.append("delivery requires complete task finalization and passed assistant QA")
    if manifest["runtime_evidence_origin"] == "deterministic_contract_fixture" and not fixture_mode:
        errors.append("deterministic fixture receipts cannot satisfy production delivery")
    if manifest["runtime_evidence_origin"] == "live_runtime" and fixture_mode:
        errors.append("fixture mode cannot be used for live runtime evidence")
    if canon["canon_freeze_status"] != "frozen" or canon["QA_status"] != "approved":
        errors.append("delivery requires frozen, QA-approved Scene Canon")
    if appearance["appearance_freeze_status"] != "frozen":
        errors.append("delivery requires frozen appearance decomposition")
    if canon["unresolved_hard_blockers"] or any(item["status"] != "approved" for item in canon["canonical_completion_elements"]):
        errors.append("delivery cannot contain unresolved blockers or unapproved completion")
    if any(item["resolution_status"] in {"unresolved", "hard_blocker"} for item in canon["conflicts"]):
        errors.append("delivery cannot contain unresolved conflicts")
    source_references = canon["source_reference_list"]
    source_ids = [item["reference_id"] for item in source_references]
    if len(source_ids) != len(set(source_ids)) or canon["primary_reference"] not in source_ids:
        errors.append("source reference IDs must be unique and include the primary reference")
    source_by_id = {item["reference_id"]: item for item in source_references}
    if not set(appearance["source_reference_ids"]).issubset(source_ids) or canon["primary_reference"] not in appearance["source_reference_ids"]:
        errors.append("appearance decomposition does not bind the primary known source")
    for source_id, source in source_by_id.items():
        source_path = require_local_file(root, source["source_locator"], f"source reference {source_id}", errors)
        if source_path is not None:
            try:
                width, height = dimensions(source_path)
                if source["dimensions"] != {"width": width, "height": height} or canon["source_asset_dimensions"].get(source_id) != {"width": width, "height": height}:
                    errors.append(f"source reference {source_id}: dimensions are stale")
            except (OSError, RuntimeError, ValueError) as exc:
                errors.append(f"source reference {source_id}: source decode failed: {exc}")
    for item in canon["source_locked_elements"] + canon["source_corroborated_elements"]:
        if not set(item["source_reference_ids"]).issubset(source_ids):
            errors.append(f"{item['element_id']}: source evidence references an unknown source")
    node_by_id, node_by_asset = validate_graph(canon, errors)
    prompts = manifest["generation_prompt_records"]
    if len(prompts) != 6:
        errors.append("delivery requires exactly six generation prompt records")
    prompt_ids = [prompt["prompt_id"] for prompt in prompts]
    prompt_asset_ids = [prompt["asset_id"] for prompt in prompts]
    if prompt_asset_ids != MACHINE_ASSET_IDS or len(prompt_ids) != len(set(prompt_ids)):
        errors.append("generation prompts must map uniquely to the ordered six assets")
    prompt_hashes = [prompt["prompt_sha256"] for prompt in prompts]
    if len(prompt_hashes) != len(set(prompt_hashes)):
        errors.append("generation prompt bodies/hashes must be unique across all six assets")
    for order, prompt in enumerate(prompts, 1):
        asset_id = MACHINE_ASSET_IDS[order - 1]
        if prompt["generation_order"] != order or prompt["dependency_stage"] != STAGES[asset_id]:
            errors.append(f"{prompt['prompt_id']}: generation order/stage mismatch")
        if prompt["dependency_asset_ids"] != DEPENDENCIES[asset_id]:
            errors.append(f"{prompt['prompt_id']}: dependency set mismatch")
        if prompt["coverage_node_id"] != node_by_asset.get(asset_id, {}).get("node_id"):
            errors.append(f"{prompt['prompt_id']}: coverage node mismatch")
        if prompt["status"] != "published":
            errors.append(f"{prompt['prompt_id']}: prompt is not published")
        if sha256_text(prompt["prompt_body"]) != prompt["prompt_sha256"]:
            errors.append(f"{prompt['prompt_id']}: prompt body hash mismatch")
        if not meaningful(prompt["prompt_body"], 400):
            errors.append(f"{prompt['prompt_id']}: prompt body is placeholder or incomplete")
        if asset_id not in prompt["prompt_body"]:
            errors.append(f"{prompt['prompt_id']}: prompt body does not identify its target asset")
        if prompt["prompt_id"] not in prompt_doc or prompt["prompt_sha256"] not in prompt_doc or prompt["prompt_body"] not in prompt_doc:
            errors.append(f"{prompt['prompt_id']}: complete prompt is missing from GENERATION_PROMPTS.md")
        plan = prompt["reference_plan"]
        if [item["index"] for item in plan] != list(range(1, len(plan) + 1)) or len(plan) > 5:
            errors.append(f"{prompt['prompt_id']}: reference plan order/count is invalid")
        planned_predecessors = [item["predecessor_asset_id"] for item in plan if item["kind"] == "approved_predecessor"]
        if planned_predecessors != DEPENDENCIES[asset_id] or len(plan) != 1 + len(DEPENDENCIES[asset_id]):
            errors.append(f"{prompt['prompt_id']}: reference plan does not bind exact ordered predecessor list")
        if not plan or plan[0]["kind"] != "source_reference" or plan[0]["source_reference_id"] != canon["primary_reference"] or plan[0]["predecessor_asset_id"] is not None:
            errors.append(f"{prompt['prompt_id']}: frozen primary scene source must be reference 1")
        if any(item["kind"] == "source_reference" for item in plan[1:]):
            errors.append(f"{prompt['prompt_id']}: prompt plan must contain exactly one source reference")
    publication = validate_prompt_publication(root, manifest, prompts, prompt_doc, errors)
    queue = manifest["generation_queue"]
    if queue["ordered_asset_ids"] != MACHINE_ASSET_IDS:
        errors.append("generation queue must use the ordered six assets")
    if mode == "delivery" and queue["status"] != "complete":
        errors.append("generation queue must complete the ordered six assets")
    if mode == "delivery" and (queue["current_asset_id"] is not None or queue["next_asset_id"] is not None):
        errors.append("complete generation queue cannot retain current/next asset")
    if mode == "stage" and queue["status"] not in {"running", "repair_required"}:
        errors.append("stage generation queue must be running or repair_required")
    if queue["user_continuation_required"] or queue["max_parallel_workers"] != 1:
        errors.append("generation must be automatic and strictly serial")
    assets = manifest["assets"]
    if len(assets) != 7 or len({asset["asset_id"] for asset in assets}) != 7:
        errors.append("delivery requires six unique machine assets plus one review board")
    machine_assets = [asset for asset in assets if asset["is_machine_asset"]]
    review_assets = [asset for asset in assets if asset["asset_type"] == "human_review_overview_board"]
    if [asset["asset_id"] for asset in machine_assets] != MACHINE_ASSET_IDS:
        errors.append("manifest machine assets must equal the ordered six-asset profile")
    if len(review_assets) != 1 or review_assets[0]["asset_id"] != "HRB_001":
        errors.append("delivery requires exactly one HRB_001 review board")
    if set(node_by_asset) != set(MACHINE_ASSET_IDS) or set(prompt_asset_ids) != set(MACHINE_ASSET_IDS):
        errors.append("graph nodes, machine assets, and generation prompts must reconcile one-to-one")
    prefix_ids = MACHINE_ASSET_IDS if mode == "delivery" else MACHINE_ASSET_IDS[: MACHINE_ASSET_IDS.index(str(through_asset)) + 1]
    generated_ids = [asset["asset_id"] for asset in machine_assets if asset["generation_status"] in {"generated", "regenerated"}]
    if mode == "stage" and generated_ids != prefix_ids:
        errors.append("stage validation must target the exact contiguous generated asset prefix")
    if not isinstance(dimensions_index, dict) or (set(dimensions_index) != set(MACHINE_ASSET_IDS) if mode == "delivery" else set(dimensions_index) != set(prefix_ids)):
        errors.append("actual_image_dimensions.json keys must equal the validated machine-asset set")
        dimensions_index = {}
    if [asset.get("asset_id") for asset in machine_assets] != MACHINE_ASSET_IDS or set(node_by_asset) != set(MACHINE_ASSET_IDS):
        return errors
    worker_threads: set[str] = set()
    worker_agents: set[str] = set()
    worker_nonces: set[str] = set()
    image_calls: set[str] = set()
    inspected_times: dict[str, int] = {}
    image_paths: dict[str, Path] = {}
    image_perceptual: dict[str, tuple[int, int, int]] = {}
    image_decoded_sha: dict[str, str] = {}
    image_thumbnails: dict[str, bytes] = {}
    inspection_id_by_asset: dict[str, str] = {}
    previous_inspection = -1
    first_spawn: int | None = None
    parent_thread_id: str | None = None
    spawn_event_indices: list[int] = []
    validated_assets = machine_assets if mode == "delivery" else machine_assets[: len(prefix_ids)]
    for order, asset in enumerate(validated_assets, 1):
        asset_id = asset["asset_id"]
        if asset["asset_type"] != TYPE_BY_ASSET[asset_id] or asset["mandatory_role"] != ROLE_BY_ASSET[asset_id]:
            errors.append(f"{asset_id}: asset type or mandatory role mismatch")
        node = node_by_asset.get(asset_id)
        if node is None or asset["coverage_node_id"] != node["node_id"]:
            errors.append(f"{asset_id}: manifest/graph back-pointer mismatch")
        if asset["generation_order"] != order or asset["dependency_stage"] != STAGES[asset_id] or asset["dependency_asset_ids"] != DEPENDENCIES[asset_id]:
            errors.append(f"{asset_id}: manifest dependency order/stage mismatch")
        if asset["generation_prompt_id"] != f"GEN_{asset_id}":
            errors.append(f"{asset_id}: generation prompt back-pointer mismatch")
        if asset["generation_status"] not in {"generated", "regenerated"} or asset["assistant_qa_status"] != "approved":
            errors.append(f"{asset_id}: required asset is not generated and approved")
        if not asset["accepted_attempt_id"]:
            errors.append(f"{asset_id}: accepted attempt is missing")
        if not asset["independently_generated"] or asset["derived_from_multipanel"] or asset["generation_mode"] != "independent_full_frame":
            errors.append(f"{asset_id}: machine asset is not an independent full-frame generation")
        if any(asset["contamination_flags"].values()):
            errors.append(f"{asset_id}: contamination flags must all be false")
        if canon["primary_reference"] not in asset["source_reference_ids"] or not set(asset["source_reference_ids"]).issubset(source_ids):
            errors.append(f"{asset_id}: asset source references do not bind the primary known source")
        if asset["canon_sha256"] != canon_hash or asset["appearance_sha256"] != appearance_hash or asset["completion_hash"] != completion_hash:
            errors.append(f"{asset_id}: asset package-state hashes are stale")
        if asset["scene_canon_version"] != manifest["canon_revision"] or asset["neutral_appearance_version"] != manifest["appearance_revision"]:
            errors.append(f"{asset_id}: asset canon/appearance revision is stale")
        image_path = require_local_file(root, asset["file_path"], f"{asset_id} image", errors)
        if image_path is None:
            continue
        image_paths[asset_id] = image_path
        actual_sha = sha256_file(image_path)
        if asset["file_sha256"] != actual_sha:
            errors.append(f"{asset_id}: image SHA-256 mismatch")
        try:
            width, height = dimensions(image_path)
            image_perceptual[asset_id] = image_hashes(image_path)
            image_decoded_sha[asset_id] = decoded_pixel_sha256(image_path)
            image_thumbnails[asset_id] = similarity_thumbnail(image_path)
        except (OSError, RuntimeError, ValueError) as exc:
            errors.append(f"{asset_id}: image decode failed: {exc}")
            continue
        if asset["actual_pixel_dimensions"] != {"width": width, "height": height} or not asset["actual_dimensions_verified"]:
            errors.append(f"{asset_id}: actual dimensions are false or unverified")
        if dimensions_index.get(asset_id) != {"file_path": asset["file_path"], "width": width, "height": height, "verified": True}:
            errors.append(f"{asset_id}: actual_image_dimensions.json is stale")
        if asset["native_4k_claim"]:
            target = asset["target_pixel_dimensions"]
            if not asset.get("native_4k_evidence") or width < target["width"] or height < target["height"]:
                errors.append(f"{asset_id}: native 4K claim lacks pixel/provenance evidence")
        worker_path = require_local_file(root, str(asset["worker_result_path"]), f"{asset_id} worker result", errors)
        inspection_path = require_local_file(root, str(asset["inspection_receipt_path"]), f"{asset_id} inspection receipt", errors)
        if worker_path is None or inspection_path is None:
            continue
        if sha256_file(worker_path) != asset["worker_result_sha256"]:
            errors.append(f"{asset_id}: worker result hash mismatch")
            continue
        if sha256_file(inspection_path) != asset["inspection_receipt_sha256"]:
            errors.append(f"{asset_id}: inspection receipt hash mismatch")
            continue
        try:
            result = read_json(worker_path)
            inspection = read_json(inspection_path)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            errors.append(f"{asset_id}: invalid runtime receipt JSON: {exc}")
            continue
        if result.get("contract") != "delegated_image_worker_result.v3" or result.get("ok") is not True:
            errors.append(f"{asset_id}: worker result is not audited v3 success")
        if result.get("binding_mode") != "parent_spawn_cipher_chain_v1" or not result.get("prompt_sha_match"):
            errors.append(f"{asset_id}: worker result lacks real parent/prompt binding")
        expected_prompt = next((item for item in prompts if item["asset_id"] == asset_id), None)
        if expected_prompt and (result.get("generation_prompt_sha256") != expected_prompt["prompt_sha256"] or result.get("tool_prompt_sha256") != expected_prompt["prompt_sha256"]):
            errors.append(f"{asset_id}: worker prompt bytes differ from published prompt")
        result_image = Path(str(result.get("run_image_path", ""))).resolve()
        if result_image != image_path or result.get("image_sha256") != actual_sha or result.get("width_px") != width or result.get("height_px") != height:
            errors.append(f"{asset_id}: worker result does not bind the manifest image")
        reference_path = Path(str(result.get("reference_manifest_path", "")))
        dependency_paths = {
            dependency: root / next(item["file_path"] for item in validated_assets if item["asset_id"] == dependency)
            for dependency in DEPENDENCIES[asset_id]
        }
        primary_source_record = source_by_id.get(canon["primary_reference"])
        expected_primary_path = root / primary_source_record["source_locator"] if primary_source_record else root / "__missing_primary_source__"
        validate_reference_manifest(
            root, reference_path, result, asset_id, canon["primary_reference"],
            expected_prompt["reference_plan"] if expected_prompt else [],
            expected_primary_path, dependency_paths, errors,
        )
        if manifest["runtime_evidence_origin"] == "live_runtime" and reference_path.is_file() and expected_prompt:
            validate_live_worker_lineage(result, expected_prompt, reference_path, errors, asset_id)
        agent = str(result.get("agent_path", ""))
        thread = str(result.get("worker_thread_id", ""))
        nonce = str(result.get("worker_run_nonce", ""))
        call = str(result.get("image_generation_call_id", ""))
        expected_worker_task = f"scene_canon_image_{asset_id.lower()}_{nonce}"
        if not agent or agent in worker_agents:
            errors.append(f"{asset_id}: worker agent path is missing or reused")
        else:
            try:
                actual_worker_task = worker_resolver.validate_worker_name_binding(agent, nonce)
                if actual_worker_task != expected_worker_task or result.get("worker_task_name") != expected_worker_task:
                    errors.append(f"{asset_id}: worker namespace does not bind the target asset")
            except worker_resolver.ContractError as exc:
                errors.append(f"{asset_id}: invalid worker namespace: {exc}")
        if result.get("asset_id") != asset_id or result.get("attempt_id") != asset["accepted_attempt_id"]:
            errors.append(f"{asset_id}: worker result does not bind asset and accepted attempt")
        if not thread or thread in worker_threads:
            errors.append(f"{asset_id}: worker thread is missing or reused")
        if not re.fullmatch(r"[0-9a-f]{32}", nonce) or nonce in worker_nonces:
            errors.append(f"{asset_id}: worker nonce is invalid or reused")
        if not call or call in image_calls:
            errors.append(f"{asset_id}: image call ID is missing or reused")
        worker_agents.add(agent); worker_threads.add(thread); worker_nonces.add(nonce); image_calls.add(call)
        result_parent = result.get("parent_thread_id")
        if not isinstance(result_parent, str) or not result_parent:
            errors.append(f"{asset_id}: worker parent thread ID is missing")
        if parent_thread_id is None:
            parent_thread_id = result_parent
        elif result.get("parent_thread_id") != parent_thread_id:
            errors.append(f"{asset_id}: workers do not share one finalizing parent task")
        spawn_time = result.get("parent_spawn_activity_ms")
        spawn_event_index = result.get("parent_spawn_event_index")
        if not isinstance(spawn_event_index, int) or spawn_event_index < 0:
            errors.append(f"{asset_id}: worker spawn event index is missing")
        else:
            spawn_event_indices.append(spawn_event_index)
        if not isinstance(spawn_time, int):
            errors.append(f"{asset_id}: worker spawn time is missing")
            continue
        if first_spawn is None:
            first_spawn = spawn_time
        if spawn_time <= previous_inspection:
            errors.append(f"{asset_id}: workers were parallelized or dispatched before prior inspection")
        for dependency in DEPENDENCIES[asset_id]:
            if spawn_time <= inspected_times.get(dependency, sys.maxsize):
                errors.append(f"{asset_id}: predecessor {dependency} was not approved before dispatch")
        if inspection.get("schema_version") != "scene_inspection_receipt.v1" or inspection.get("origin") != manifest["runtime_evidence_origin"]:
            errors.append(f"{asset_id}: inspection receipt schema/origin mismatch")
        receipt_id = inspection.get("receipt_id")
        if not isinstance(receipt_id, str) or not receipt_id:
            errors.append(f"{asset_id}: inspection receipt ID is missing")
        else:
            inspection_id_by_asset[asset_id] = receipt_id
        if inspection.get("asset_id") != asset_id or inspection.get("coverage_node_id") != asset["coverage_node_id"]:
            errors.append(f"{asset_id}: inspection receipt targets the wrong asset/node")
        if inspection.get("inspector_task_id") != parent_thread_id:
            errors.append(f"{asset_id}: inspection owner is not the finalizing parent task")
        if inspection.get("worker_result_path") != asset["worker_result_path"] or inspection.get("worker_result_sha256") != asset["worker_result_sha256"]:
            errors.append(f"{asset_id}: inspection does not bind worker result")
        if inspection.get("image_path") != asset["file_path"] or inspection.get("image_sha256") != actual_sha:
            errors.append(f"{asset_id}: inspection does not bind image bytes")
        inspected = inspection.get("inspected_elapsed_ms")
        if not isinstance(inspected, int) or inspected <= spawn_time:
            errors.append(f"{asset_id}: main-agent inspection must follow worker spawn/result")
            continue
        inspected_times[asset_id] = inspected
        previous_inspection = inspected
        if inspection.get("decision") != "approved" or not meaningful(str(inspection.get("evidence_summary", "")), 40):
            errors.append(f"{asset_id}: inspection is not approved with substantive evidence")
        checks = inspection.get("checks")
        required_checks = {"source_fidelity", "topology", "scale", "landmarks", "materials", "fixed_content", "overlap", "reveal", "parallax", "loop_continuity", "duplicate", "contamination", "neutral_appearance"}
        if not isinstance(checks, dict) or set(checks) != required_checks or any(value is not True for value in checks.values()):
            errors.append(f"{asset_id}: inspection hard-gate checks are incomplete")
        if not set(node.get("visible_landmark_ids", [])).issubset(set(inspection.get("observed_landmark_ids", []))):
            errors.append(f"{asset_id}: inspection does not observe required landmarks")
        if not set(node.get("revealed_region_ids", [])).issubset(set(inspection.get("observed_revealed_region_ids", []))):
            errors.append(f"{asset_id}: inspection does not bind required reveal regions")
    if len(inspection_id_by_asset) != len(set(inspection_id_by_asset.values())):
        errors.append("inspection receipt IDs must be unique across machine assets")
    if publication and first_spawn is not None:
        if publication["first_worker_spawn_elapsed_ms"] != first_spawn or queue["first_worker_spawn_elapsed_ms"] != first_spawn:
            errors.append("first worker spawn time is inconsistent across publication receipt, queue, and runtime")
        if publication.get("parent_thread_id") != parent_thread_id:
            errors.append("prompt publication and workers do not share the finalizing parent task")
        if spawn_event_indices and (
            publication.get("first_worker_spawn_event_index") != min(spawn_event_indices)
            or spawn_event_indices != sorted(set(spawn_event_indices))
            or any(index <= publication.get("publication_event_index", -1) for index in spawn_event_indices)
        ):
            errors.append("all worker spawn events must follow the bound prompt publication event")
    if inspected_times and queue["last_worker_complete_elapsed_ms"] != max(inspected_times.values()):
        errors.append("queue last completion time does not match final inspection")
    file_hashes = [asset["file_sha256"] for asset in validated_assets]
    if len(file_hashes) != len(set(file_hashes)):
        errors.append("exact duplicate image bytes across machine assets")
    for left_id, right_id in combinations(prefix_ids, 2):
        if left_id not in image_perceptual or right_id not in image_perceptual:
            continue
        distances = [hamming(a, b) for a, b in zip(image_perceptual[left_id], image_perceptual[right_id])]
        left_node = node_by_asset.get(left_id, {})
        right_node = node_by_asset.get(right_id, {})
        left_pose = left_node.get("camera_pose", {})
        right_pose = right_node.get("camera_pose", {})
        pose_close = sum(abs(float(left_pose.get(axis, 0)) - float(right_pose.get(axis, 0))) for axis in ("x", "y", "z")) <= 0.08 and abs(float(left_pose.get("yaw_degrees", 0)) - float(right_pose.get("yaw_degrees", 0))) <= 3
        information_same = set(left_node.get("revealed_region_ids", [])) == set(right_node.get("revealed_region_ids", [])) and set(left_node.get("visible_landmark_ids", [])) == set(right_node.get("visible_landmark_ids", []))
        left_thumb = image_thumbnails.get(left_id, b"")
        right_thumb = image_thumbnails.get(right_id, b"")
        mean_absolute_difference = (
            sum(abs(left - right) for left, right in zip(left_thumb, right_thumb)) / len(left_thumb)
            if left_thumb and len(left_thumb) == len(right_thumb)
            else 255.0
        )
        if image_decoded_sha.get(left_id) == image_decoded_sha.get(right_id) or (min(distances) <= 2 and (mean_absolute_difference <= 4.0 or pose_close or information_same)):
            errors.append(f"near-duplicate or crop/focal-only coverage: {left_id} and {right_id}")
    if mode == "stage":
        return errors
    review = review_assets[0] if review_assets else None
    if review:
        if review["is_machine_asset"] or review["generation_mode"] != "approved_asset_composite" or review["generation_prompt_id"] is not None or review["four_k_prompt_id"] is not None:
            errors.append("HRB_001 must be a non-machine approved-asset composite")
        if review["coverage_node_id"] is not None or review["asset_id"] in node_by_asset:
            errors.append("HRB_001 cannot enter the coverage graph")
        review_path = require_local_file(root, review["file_path"], "HRB_001", errors)
        if manifest["human_review_overview_board"] != review["file_path"]:
            errors.append("manifest human review board back-pointer mismatch")
        if review_path:
            if review_path in image_paths.values() or review["file_sha256"] in file_hashes:
                errors.append("HRB_001 cannot reuse a machine asset path or bytes")
            if sha256_file(review_path) != review["file_sha256"]:
                errors.append("HRB_001 hash mismatch")
            try:
                width, height = dimensions(review_path)
                if review["actual_pixel_dimensions"] != {"width": width, "height": height} or not review["actual_dimensions_verified"]:
                    errors.append("HRB_001 dimensions are false or unverified")
                expected_board, selected_count = compose_review_board(manifest_path)
                with Image.open(review_path) as actual_board:
                    actual_pixels = actual_board.convert("RGB")
                if selected_count != 6 or actual_pixels.size != expected_board.size or actual_pixels.tobytes() != expected_board.tobytes():
                    errors.append("HRB_001 is not the deterministic composite of all six approved machine assets")
            except (OSError, RuntimeError, ValueError) as exc:
                errors.append(f"HRB_001 decode failed: {exc}")
    four_k_records = manifest["four_k_prompt_records"]
    finalized = [record for record in four_k_records if record["status"] == "finalized_post_qa"]
    expected_four_k_ids = [f"4K_{asset_id}" for asset_id in MACHINE_ASSET_IDS]
    if len(finalized) != 6 or [record["asset_id"] for record in finalized] != MACHINE_ASSET_IDS:
        errors.append("delivery requires exactly one finalized 4K prompt per machine asset")
    finalized_prompt_ids = [record["prompt_id"] for record in finalized]
    if len(four_k_records) != 6 or len(finalized_prompt_ids) != len(set(finalized_prompt_ids)):
        errors.append("4K prompt IDs must be unique with no extra or non-finalized records")
    if finalized_prompt_ids != expected_four_k_ids:
        errors.append("4K prompt records must use the ordered one-to-one asset prompt IDs")
    four_k_doc = (root / "08_4k_regeneration/4K_ASSET_REGENERATION_PROMPTS.md").read_text(encoding="utf-8")
    asset_by_id = {asset["asset_id"]: asset for asset in machine_assets}
    four_k_bodies = [record["regeneration_prompt_en"] for record in finalized]
    if len(four_k_bodies) != len(set(four_k_bodies)):
        errors.append("4K regeneration prompt bodies must be unique per asset")
    for record in finalized:
        asset = asset_by_id.get(record["asset_id"])
        if asset is None:
            continue
        if record["primary_reference_asset_id"] != asset["asset_id"] or record["source_image"] != asset["file_path"]:
            errors.append(f"{record['prompt_id']}: matching neutral asset is not primary")
        if record["target_dimensions"] != canon["target_4k_dimensions"] or asset["target_pixel_dimensions"] != canon["target_4k_dimensions"] or record["target_dimensions"]["width"] < 3840 or record["target_dimensions"]["height"] < 2160:
            errors.append(f"{record['prompt_id']}: target dimensions are not the frozen 4K target")
        if record["required_reference_images"] != [asset["file_path"]]:
            errors.append(f"{record['prompt_id']}: required references must contain only the matching approved asset first")
        for reference in record["required_reference_images"]:
            require_local_file(root, reference, f"{record['prompt_id']} required reference", errors)
        if record["source_dimensions"] != asset["actual_pixel_dimensions"] or record["source_asset_sha256"] != asset["file_sha256"]:
            errors.append(f"{record['prompt_id']}: stale source image binding")
        if record["source_asset_revision"] != asset["asset_revision"] or record["source_canon_sha256"] != canon_hash or record["source_appearance_sha256"] != appearance_hash or record["source_completion_hash"] != completion_hash:
            errors.append(f"{record['prompt_id']}: stale canon/appearance/completion binding")
        if asset["four_k_prompt_id"] != record["prompt_id"] or record["prompt_id"] not in four_k_doc:
            errors.append(f"{record['prompt_id']}: manifest/Markdown 4K mapping mismatch")
        lower = record["regeneration_prompt_en"].lower()
        if asset["asset_name"].lower() not in lower:
            errors.append(f"{record['prompt_id']}: regeneration prompt is not asset-specific")
        for phrase in ("primary and highest-priority", "do not restore", "do not redesign"):
            if phrase not in lower:
                errors.append(f"{record['prompt_id']}: regeneration prompt lacks {phrase!r}")
    if manifest["approved_machine_asset_count"] != 6 or manifest["four_k_prompt_mapping_count"] != 6:
        errors.append("approved machine and 4K mapping counts must both equal six")
    if set(canon["generated_asset_index"]) != set(MACHINE_ASSET_IDS + ["HRB_001"]):
        errors.append("Scene Canon generated_asset_index is incomplete")
    asset_four_k_ids = [asset["four_k_prompt_id"] for asset in machine_assets]
    if canon["four_k_prompt_index"] != expected_four_k_ids or asset_four_k_ids != expected_four_k_ids or finalized_prompt_ids != expected_four_k_ids:
        errors.append("Scene Canon, assets, and 4K records must share one ordered one-to-one prompt index")
    qa_records = manifest["structured_qa_records"]
    if not qa_records:
        errors.append("structured QA records are required")
    required_package_checks = {"prompt_publication", "runtime_lineage", "duplicate_detection", "four_k_mapping"}
    present_package_checks = {record["check_id"] for record in qa_records if record["scope"] == "package"}
    if not required_package_checks.issubset(present_package_checks):
        errors.append("structured package QA is missing required checks")
    check_ids = [record["check_id"] for record in qa_records]
    if len(check_ids) != len(set(check_ids)):
        errors.append("structured QA check IDs must be unique")
    node_asset_by_id = {node["node_id"]: node["asset_id"] for node in canon["coverage_graph"]["nodes"]}
    edge_assets = {
        edge["edge_id"]: [asset_id for node_id in (edge["from_node_id"], edge["to_node_id"]) if (asset_id := node_asset_by_id.get(node_id))]
        for edge in canon["coverage_graph"]["edges"]
    }
    path_assets = {
        path["path_id"]: [asset_id for node_id in path["node_ids"] if (asset_id := node_asset_by_id.get(node_id))]
        for path in canon["coverage_graph"]["paths"]
    }
    loop_assets = {
        loop["loop_id"]: [asset_id for node_id in loop["node_ids"] if (asset_id := node_asset_by_id.get(node_id))]
        for loop in canon["coverage_graph"]["loops"]
    }
    expected_bindings: dict[tuple[str, str], list[str]] = {
        **{("asset", asset_id): [asset_id] for asset_id in MACHINE_ASSET_IDS},
        **{("edge", key): value for key, value in edge_assets.items()},
        **{("path", key): value for key, value in path_assets.items()},
        **{("loop", key): value for key, value in loop_assets.items()},
    }
    all_asset_hashes = [asset_by_id[asset_id]["file_sha256"] for asset_id in MACHINE_ASSET_IDS]
    all_inspection_ids = [inspection_id_by_asset.get(asset_id, "") for asset_id in MACHINE_ASSET_IDS]
    for record in qa_records:
        if record["status"] != "passed" or not meaningful(record["evidence_summary"], 20):
            errors.append(f"{record['check_id']}: structured QA is failed or placeholder")
        if len(record["subject_ids"]) != 1:
            errors.append(f"{record['check_id']}: structured QA must bind exactly one declared subject")
            continue
        subject = record["subject_ids"][0]
        if record["scope"] == "package":
            if subject != manifest["package_id"] or record["bound_asset_sha256"] != all_asset_hashes or record["inspection_receipt_ids"] != all_inspection_ids:
                errors.append(f"{record['check_id']}: package QA does not bind all six assets and inspections in order")
            continue
        expected_assets = expected_bindings.get((record["scope"], subject))
        if expected_assets is None:
            errors.append(f"{record['check_id']}: structured QA subject does not exist")
            continue
        expected_hashes = [asset_by_id[asset_id]["file_sha256"] for asset_id in expected_assets]
        expected_receipts = [inspection_id_by_asset.get(asset_id, "") for asset_id in expected_assets]
        if record["bound_asset_sha256"] != expected_hashes or record["inspection_receipt_ids"] != expected_receipts:
            errors.append(f"{record['check_id']}: structured QA bindings are stale or incomplete")
    for asset_id in MACHINE_ASSET_IDS:
        if not any(record["scope"] == "asset" and asset_id in record["subject_ids"] for record in qa_records):
            errors.append(f"{asset_id}: structured asset QA record is missing")
    for edge in canon["coverage_graph"]["edges"]:
        if not any(record["scope"] == "edge" and edge["edge_id"] in record["subject_ids"] for record in qa_records):
            errors.append(f"{edge['edge_id']}: structured edge QA record is missing")
    for path in canon["coverage_graph"]["paths"]:
        if not any(record["scope"] == "path" and path["path_id"] in record["subject_ids"] for record in qa_records):
            errors.append(f"{path['path_id']}: structured path QA record is missing")
    for loop in canon["coverage_graph"]["loops"]:
        if not any(record["scope"] == "loop" and loop["loop_id"] in record["subject_ids"] for record in qa_records):
            errors.append(f"{loop['loop_id']}: structured loop QA record is missing")
    for rel in [
        "09_qa/QA_REPORT.md", "09_qa/look_contamination_report.md", "09_qa/coverage_graph_report.md",
        "09_qa/4k_prompt_mapping_report.md", "01_source_analysis/source_evidence_report.md",
        "01_source_analysis/conflict_report.md", "01_source_analysis/coverage_assessment.md",
    ]:
        text = (root / rel).read_text(encoding="utf-8")
        if not meaningful(text, 80):
            errors.append(f"{rel}: report is placeholder or lacks substantive evidence")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package_root", type=Path)
    parser.add_argument("--mode", choices=["state", "stage", "delivery"], default="delivery")
    parser.add_argument("--through-asset", choices=MACHINE_ASSET_IDS)
    parser.add_argument("--fixture-mode", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    errors = validate_package(args.package_root, mode=args.mode, fixture_mode=args.fixture_mode, through_asset=args.through_asset)
    if errors:
        label = f"scene canon {args.mode} validation"
        print(f"{label}: FAILED")
        for error in errors:
            print(f"  - {error}")
        return 1
    if args.mode in {"state", "stage"}:
        print(f"scene canon {args.mode} validation: STATE_VALID_NOT_COMPLETE")
    else:
        print("scene canon delivery validation: DELIVERY_VALIDATED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
