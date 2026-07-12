#!/usr/bin/env python3
"""Measure exact product copy and codes on final composed packaging masters.

This adapter is intentionally fail closed.  It always invokes the bundled
``macos_vision_ocr.swift`` adapter with language correction disabled by that
adapter; callers cannot select another OCR engine or script.  It scans every
complete final master and also scans crops derived from the destination regions
in the immutable composition job.  Exact-copy approval is emitted only when
every expected field/code has one and only one exact observation and there are
no unexplained text or code observations.

The command writes candidate evidence.  It never edits run_manifest.json or
silently promotes the candidate into the run's locked post-verification file.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

try:
    from PIL import Image
except ImportError:  # pragma: no cover - capability failure on an invalid host
    Image = None  # type: ignore[assignment]


SKILL_DIR = Path(__file__).resolve().parents[1]
VISION_SCRIPT = SKILL_DIR / "scripts/macos_vision_ocr.swift"
COMPOSITOR_SCRIPT = SKILL_DIR / "scripts/compose_exact_copy.py"
ENGINE_ID = "bundled_macos_vision_ocr"
ENGINE_SCRIPT_LOCATOR = "scripts/macos_vision_ocr.swift"
ADAPTER_LOCATOR = "scripts/run_post_composite_verification.py"
DEFAULT_OUTPUT = "07_qa/post_composite_verification.candidate.json"
OCR_MATCH_POLICIES = {"single_observation_exact", "ordered_line_aggregation_exact"}
LINE_JOINERS = {"newline": "\n", "space": " ", "none": ""}
# Fixed reading-order rule for aggregate OCR.  Coordinates are normalized to
# each crop.  Candidates whose vertical centers differ by no more than the
# larger of 0.0025 or 35% of their larger height are one line.
SAME_LINE_MIN_CENTER_DELTA = 0.0025
SAME_LINE_HEIGHT_RATIO = 0.35
INTRA_LINE_JOINER = " "


class VerificationError(RuntimeError):
    """An input or runtime condition prevents trustworthy verification."""


@dataclass(frozen=True)
class ScanSpec:
    scan_id: str
    scope: str
    image_path: Path
    image_locator: str
    crop_box_px: tuple[int, int, int, int] | None
    region_ids: tuple[str, ...]
    field_ids: tuple[str, ...]
    code_ids: tuple[str, ...]
    graphic_ids: tuple[str, ...]
    layer_ids: tuple[str, ...]


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def sha256_text(value: str) -> str:
    """Hash exact Unicode code points as their UTF-8 byte sequence."""
    return sha256_bytes(value.encode("utf-8"))


def canonical_hash(value: dict[str, Any], omit: str | None = None) -> str:
    payload = dict(value)
    if omit:
        payload.pop(omit, None)
    return sha256_bytes(json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8"))


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(
        path.read_text(encoding="utf-8"),
        parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
    )
    if not isinstance(value, dict):
        raise VerificationError(f"JSON root must be an object: {path}")
    return value


def safe_path(root: Path, locator: Any, label: str, *, must_exist: bool = True) -> Path:
    if not isinstance(locator, str) or not locator:
        raise VerificationError(f"{label}: locator must be a non-empty string")
    relative = Path(locator)
    if relative.is_absolute() or ".." in relative.parts:
        raise VerificationError(f"{label}: locator must be run-relative and cannot contain '..'")
    resolved_root = root.resolve()
    candidate = (resolved_root / relative).resolve()
    try:
        candidate.relative_to(resolved_root)
    except ValueError as exc:
        raise VerificationError(f"{label}: locator escapes the run root") from exc
    if must_exist and not candidate.is_file():
        raise VerificationError(f"{label}: missing file {locator}")
    return candidate


def run_relative_locator(root: Path, path: Path, label: str) -> str:
    """Return a run-relative locator after canonicalizing filesystem aliases.

    macOS exposes the same temporary tree as both ``/var`` and
    ``/private/var``.  Comparing unresolved ``Path`` objects makes a child of
    the same physical run appear outside its root.  Resolve both sides before
    containment and serialization; never catch-and-accept a real escape.
    """
    resolved_root = root.resolve()
    resolved_path = path.resolve()
    try:
        relative = resolved_path.relative_to(resolved_root)
    except ValueError as exc:
        raise VerificationError(f"{label}: path escapes the canonical run root") from exc
    return relative.as_posix()


def strict_identifier_set(value: Any, label: str) -> set[str]:
    if not isinstance(value, list):
        raise VerificationError(f"{label}: expected an array")
    if not all(isinstance(item, str) and item for item in value):
        raise VerificationError(f"{label}: identifiers must be non-empty strings")
    result = set(value)
    if len(result) != len(value):
        raise VerificationError(f"{label}: identifiers must be unique")
    return result


def validate_text_match_contract(fields: dict[str, dict[str, Any]]) -> None:
    for field_id, field in fields.items():
        policy = field.get("ocr_match_policy")
        joiner = field.get("line_joiner")
        if policy not in OCR_MATCH_POLICIES:
            raise VerificationError(
                f"Text SSOT {field_id}: ocr_match_policy must be one of {sorted(OCR_MATCH_POLICIES)}"
            )
        if joiner not in LINE_JOINERS:
            raise VerificationError(
                f"Text SSOT {field_id}: line_joiner must be newline, space, or none"
            )
        if policy == "single_observation_exact" and joiner != "none":
            raise VerificationError(
                f"Text SSOT {field_id}: single_observation_exact requires line_joiner=none"
            )
        text = field.get("expected_raw_text")
        if not isinstance(text, str) or not text:
            raise VerificationError(f"Text SSOT {field_id}: expected_raw_text must be non-empty")
        if field.get("expected_text_sha256") != sha256_text(text):
            raise VerificationError(f"Text SSOT {field_id}: expected_text_sha256 is stale")


def load_locked_manifest_json(
    root: Path, manifest: dict[str, Any], path_key: str, hash_key: str,
) -> tuple[Path, dict[str, Any]]:
    paths = manifest.get("paths")
    hashes = manifest.get("hashes")
    if not isinstance(paths, dict) or not isinstance(hashes, dict):
        raise VerificationError("run manifest paths/hashes must be objects")
    path = safe_path(root, paths.get(path_key), f"manifest.paths.{path_key}")
    expected_hash = hashes.get(hash_key)
    actual_hash = sha256_file(path)
    if expected_hash != actual_hash:
        raise VerificationError(
            f"{path_key}: manifest hash is missing or stale; expected {expected_hash!r}, "
            f"observed {actual_hash}"
        )
    return path, read_json(path)


def verify_image(path: Path) -> tuple[int, int]:
    if Image is None:
        raise VerificationError("Pillow is required to inspect and crop final masters")
    try:
        with Image.open(path) as probe:
            size = probe.size
            probe.verify()
        with Image.open(path) as decoded:
            decoded.load()
    except Exception as exc:
        raise VerificationError(f"image is not fully decodable: {path}: {exc}") from exc
    if size[0] < 1 or size[1] < 1:
        raise VerificationError(f"image has invalid dimensions: {path}")
    return size


def atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def load_bundled_module(path: Path, module_name: str) -> Any:
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise VerificationError(f"cannot load bundled module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_destination_box(
    layer: dict[str, Any], canvas_size: tuple[int, int], label: str,
) -> tuple[int, int, int, int]:
    width, height = canvas_size
    model = layer.get("projection_model")
    if model in {"source_pixel_preservation", "planar_rectangle"}:
        value = layer.get("destination_box_px")
        if (
            not isinstance(value, list) or len(value) != 4
            or not all(isinstance(item, int) and not isinstance(item, bool) for item in value)
        ):
            raise VerificationError(f"{label}: destination_box_px must be four integers")
        left, top, right, bottom = value
    elif model == "planar_homography":
        value = layer.get("destination_quad_px")
        if not isinstance(value, list) or len(value) != 4:
            raise VerificationError(f"{label}: destination_quad_px must contain four points")
        points: list[tuple[float, float]] = []
        for point in value:
            if (
                not isinstance(point, list) or len(point) != 2
                or not all(isinstance(axis, (int, float)) and not isinstance(axis, bool) for axis in point)
            ):
                raise VerificationError(f"{label}: destination quad points must be numeric [x,y]")
            points.append((float(point[0]), float(point[1])))
        left = math.floor(min(point[0] for point in points))
        top = math.floor(min(point[1] for point in points))
        right = math.ceil(max(point[0] for point in points))
        bottom = math.ceil(max(point[1] for point in points))
    else:
        raise VerificationError(f"{label}: unsupported projection_model {model!r}")
    if left < 0 or top < 0 or right <= left or bottom <= top or right > width or bottom > height:
        raise VerificationError(f"{label}: projected destination region is empty or outside final master")
    return int(left), int(top), int(right), int(bottom)


def full_master_box(
    box: Any, scan: ScanSpec, canvas_size: tuple[int, int], scan_size: tuple[int, int],
) -> dict[str, float] | None:
    if not isinstance(box, dict):
        return None
    try:
        x = float(box["x"]); y = float(box["y"])
        width = float(box["width"]); height = float(box["height"])
    except (KeyError, TypeError, ValueError):
        return None
    if x < 0 or y < 0 or width <= 0 or height <= 0 or x + width > 1.000001 or y + height > 1.000001:
        return None
    if scan.crop_box_px is None:
        return {"x": x, "y": y, "width": width, "height": height}
    left, top, right, bottom = scan.crop_box_px
    crop_width, crop_height = right - left, bottom - top
    if scan_size != (crop_width, crop_height):
        raise VerificationError(f"{scan.scan_id}: crop pixels changed before OCR")
    canvas_width, canvas_height = canvas_size
    return {
        "x": (left + x * crop_width) / canvas_width,
        "y": (canvas_height - bottom + y * crop_height) / canvas_height,
        "width": width * crop_width / canvas_width,
        "height": height * crop_height / canvas_height,
    }


def intersection_over_min_area(first: Any, second: Any) -> float:
    if not isinstance(first, dict) or not isinstance(second, dict):
        return 0.0
    try:
        left = max(float(first["x"]), float(second["x"]))
        bottom = max(float(first["y"]), float(second["y"]))
        right = min(float(first["x"]) + float(first["width"]), float(second["x"]) + float(second["width"]))
        top = min(float(first["y"]) + float(first["height"]), float(second["y"]) + float(second["height"]))
        intersection = max(0.0, right - left) * max(0.0, top - bottom)
        first_area = float(first["width"]) * float(first["height"])
        second_area = float(second["width"]) * float(second["height"])
    except (KeyError, TypeError, ValueError):
        return 0.0
    minimum = min(first_area, second_area)
    return intersection / minimum if minimum > 0 else 0.0


def canonical_symbology(raw: str) -> str:
    """Map only explicit Vision aliases to stable packaging names."""
    aliases = {
        "VNBarcodeSymbologyAztec": "AZTEC",
        "VNBarcodeSymbologyCodabar": "CODABAR",
        "VNBarcodeSymbologyCode39": "CODE-39",
        "VNBarcodeSymbologyCode39Checksum": "CODE-39-CHECKSUM",
        "VNBarcodeSymbologyCode93": "CODE-93",
        "VNBarcodeSymbologyCode93i": "CODE-93I",
        "VNBarcodeSymbologyCode128": "CODE-128",
        "VNBarcodeSymbologyDataMatrix": "DATA-MATRIX",
        "VNBarcodeSymbologyEAN8": "EAN-8",
        "VNBarcodeSymbologyEAN13": "EAN-13",
        "VNBarcodeSymbologyGS1DataBar": "GS1-DATABAR",
        "VNBarcodeSymbologyGS1DataBarExpanded": "GS1-DATABAR-EXPANDED",
        "VNBarcodeSymbologyGS1DataBarLimited": "GS1-DATABAR-LIMITED",
        "VNBarcodeSymbologyI2of5": "ITF",
        "VNBarcodeSymbologyI2of5Checksum": "ITF-CHECKSUM",
        "VNBarcodeSymbologyITF14": "ITF-14",
        "VNBarcodeSymbologyMicroPDF417": "MICRO-PDF417",
        "VNBarcodeSymbologyMicroQR": "MICRO-QR",
        "VNBarcodeSymbologyPDF417": "PDF417",
        "VNBarcodeSymbologyQR": "QR",
        "VNBarcodeSymbologyUPCE": "UPC-E",
    }
    packaging_aliases = {
        "EAN13": "EAN-13", "EAN-13": "EAN-13",
        "EAN8": "EAN-8", "EAN-8": "EAN-8",
        "QRCODE": "QR", "QR-CODE": "QR", "QR": "QR",
        "CODE128": "CODE-128", "CODE-128": "CODE-128",
        "CODE39": "CODE-39", "CODE-39": "CODE-39",
        "DATAMATRIX": "DATA-MATRIX", "DATA-MATRIX": "DATA-MATRIX",
        "UPCA": "UPC-A", "UPC-A": "UPC-A",
        "UPCE": "UPC-E", "UPC-E": "UPC-E",
        "ITF14": "ITF-14", "ITF-14": "ITF-14",
        "PDF417": "PDF417", "AZTEC": "AZTEC",
    }
    if raw in aliases:
        return aliases[raw]
    return packaging_aliases.get(raw.upper().replace("_", "-"), raw)


def numeric_mod10_checksum(payload: str, total_length: int) -> bool:
    if len(payload) != total_length or not payload.isdigit():
        return False
    digits = [int(character) for character in payload]
    body = digits[:-1]
    weighted = sum(
        digit * (3 if (len(body) - index) % 2 == 1 else 1)
        for index, digit in enumerate(body)
    )
    return (10 - weighted % 10) % 10 == digits[-1]


def decoded_payload_integrity(symbology: str, payload: str) -> tuple[bool, str]:
    canonical = canonical_symbology(symbology)
    if canonical == "EAN-13":
        return numeric_mod10_checksum(payload, 13), "ean13_mod10"
    if canonical == "EAN-8":
        return numeric_mod10_checksum(payload, 8), "ean8_mod10"
    if canonical == "UPC-A":
        return numeric_mod10_checksum(payload, 12), "upca_mod10"
    if payload:
        return True, "vision_decoder_integrity"
    return False, "empty_payload"


def run_bundled_vision(paths: list[Path], languages: list[str]) -> tuple[list[dict[str, Any]], str]:
    if platform.system() != "Darwin":
        raise VerificationError("blocked_ocr_capability: bundled macOS Vision OCR requires macOS")
    swift = shutil.which("swift")
    if not swift or not VISION_SCRIPT.is_file():
        raise VerificationError("blocked_ocr_capability: bundled macOS Vision OCR adapter is unavailable")
    env = dict(os.environ)
    env["PACKAGING_OCR_LANGUAGES"] = ",".join(languages)
    result = subprocess.run(
        [swift, str(VISION_SCRIPT), *[str(path) for path in paths]],
        check=False, capture_output=True, text=True, env=env,
    )
    if result.returncode != 0:
        raise VerificationError(
            f"bundled macOS Vision OCR failed ({result.returncode}): {result.stderr.strip()}"
        )
    try:
        value = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise VerificationError(f"bundled macOS Vision OCR returned invalid JSON: {exc}") from exc
    if not isinstance(value, list) or len(value) != len(paths):
        raise VerificationError("bundled macOS Vision OCR result count does not match scan count")
    if not all(isinstance(item, dict) for item in value):
        raise VerificationError("bundled macOS Vision OCR returned a malformed result record")
    return value, platform.mac_ver()[0] or "unknown-macos"


def make_scan_specs(
    root: Path, view_id: str, master_path: Path, job: dict[str, Any],
    canvas_size: tuple[int, int], replace: bool,
) -> list[ScanSpec]:
    scans = [ScanSpec(
        scan_id=f"{view_id}_FINAL_MASTER",
        scope="final_master",
        image_path=master_path,
        image_locator=run_relative_locator(root, master_path, f"{view_id}.final_master"),
        crop_box_px=None, region_ids=(), field_ids=(), code_ids=(), graphic_ids=(), layer_ids=(),
    )]
    layers = job.get("layers")
    if not isinstance(layers, list) or not layers:
        raise VerificationError(f"{view_id}: composition job layers must be non-empty")
    grouped: dict[
        tuple[tuple[int, int, int, int], tuple[str, ...], tuple[str, ...], tuple[str, ...], tuple[str, ...]],
        list[str],
    ] = {}
    for index, layer in enumerate(layers):
        if not isinstance(layer, dict):
            raise VerificationError(f"{view_id}: composition layer {index} is not an object")
        layer_id = layer.get("layer_id")
        if not isinstance(layer_id, str) or not layer_id:
            raise VerificationError(f"{view_id}: composition layer {index} lacks layer_id")
        box = parse_destination_box(layer, canvas_size, f"{view_id}.{layer_id}")
        region_ids = tuple(sorted({str(value) for value in layer.get("region_ids", []) if isinstance(value, str)}))
        field_ids = tuple(sorted({str(value) for value in layer.get("field_ids", []) if isinstance(value, str)}))
        code_ids = tuple(sorted({str(value) for value in layer.get("code_ids", []) if isinstance(value, str)}))
        graphic_ids = tuple(sorted({str(value) for value in layer.get("graphic_ids", []) if isinstance(value, str)}))
        key = (box, region_ids, field_ids, code_ids, graphic_ids)
        grouped.setdefault(key, []).append(layer_id)
    if Image is None:
        raise VerificationError("Pillow is required to create projected-region OCR crops")
    with Image.open(master_path) as decoded:
        decoded.load()
        for index, (key, layer_ids) in enumerate(sorted(grouped.items()), start=1):
            box, region_ids, field_ids, code_ids, graphic_ids = key
            crop_path = root / "07_qa/post_ocr/crops" / view_id / f"REGION_{index:03d}.png"
            if crop_path.exists() and not replace:
                raise VerificationError(
                    f"immutable candidate crop already exists: {crop_path}; use --replace-candidate to rerun"
                )
            crop_path.parent.mkdir(parents=True, exist_ok=True)
            temporary = crop_path.with_name(crop_path.name + ".tmp")
            decoded.crop(box).convert("RGB").save(temporary, format="PNG", optimize=False, compress_level=6)
            os.replace(temporary, crop_path)
            scans.append(ScanSpec(
                scan_id=f"{view_id}_PROJECTED_REGION_{index:03d}",
                scope="projected_region_crop",
                image_path=crop_path,
                image_locator=run_relative_locator(root, crop_path, f"{view_id}.projected_crop"),
                crop_box_px=box,
                region_ids=region_ids,
                field_ids=field_ids,
                code_ids=code_ids,
                graphic_ids=graphic_ids,
                layer_ids=tuple(sorted(layer_ids)),
            ))
    return scans


def cluster_physical_observations(
    observations: list[dict[str, Any]], identity_keys: tuple[str, ...],
) -> list[list[dict[str, Any]]]:
    groups: list[list[dict[str, Any]]] = []
    for observation in observations:
        matched: list[dict[str, Any]] | None = None
        for group in groups:
            representative = group[0]
            if not all(observation.get(key) == representative.get(key) for key in identity_keys):
                continue
            if intersection_over_min_area(
                observation.get("full_master_bounding_box_normalized"),
                representative.get("full_master_bounding_box_normalized"),
            ) >= 0.60:
                matched = group
                break
        if matched is None:
            groups.append([observation])
        else:
            matched.append(observation)
    return groups


def choose_representative(group: list[dict[str, Any]]) -> dict[str, Any]:
    return sorted(
        group,
        key=lambda item: (
            0 if item.get("scan_scope") in {
                "projected_region_aggregate", "projected_region_crop",
            } else 1,
            len(item.get("candidate_ids") or []),
            -float(item.get("confidence", 0.0)),
            str(item.get("raw_observation_id")),
        ),
    )[0]


def normalized_box_metrics(value: Any, label: str) -> tuple[float, float, float, float]:
    if not isinstance(value, dict):
        raise VerificationError(f"{label}: OCR fragment bounding box is missing")
    try:
        x = float(value["x"]); y = float(value["y"])
        width = float(value["width"]); height = float(value["height"])
    except (KeyError, TypeError, ValueError) as exc:
        raise VerificationError(f"{label}: OCR fragment bounding box is malformed") from exc
    if x < 0 or y < 0 or width <= 0 or height <= 0 or x + width > 1.000001 or y + height > 1.000001:
        raise VerificationError(f"{label}: OCR fragment bounding box is outside its scan")
    return x, y, width, height


def ordered_line_aggregation(
    fragments: list[dict[str, Any]], line_joiner: str,
) -> tuple[str, list[list[dict[str, Any]]]]:
    """Aggregate one crop's raw fragments with a frozen geometric order.

    Vision uses bottom-left normalized coordinates.  Lines are traversed from
    top to bottom; fragments inside one line are traversed left to right.  A
    single ASCII space joins fragments inside a line.  ``line_joiner`` controls
    only the boundary between geometric lines.  No Unicode, spelling, spacing,
    punctuation, or language-model correction is applied to fragment text.
    """
    if line_joiner not in LINE_JOINERS:
        raise VerificationError("ordered OCR aggregation received an invalid line_joiner")
    prepared: list[tuple[dict[str, Any], float, float, float, float]] = []
    for fragment in fragments:
        x, y, width, height = normalized_box_metrics(
            fragment.get("scan_bounding_box_normalized"),
            str(fragment.get("raw_observation_id", "OCR_FRAGMENT")),
        )
        prepared.append((fragment, x, y + height / 2.0, width, height))
    prepared.sort(key=lambda value: (-value[2], value[1], str(value[0].get("raw_observation_id"))))
    lines: list[dict[str, Any]] = []
    for fragment, x, center_y, width, height in prepared:
        selected: dict[str, Any] | None = None
        for line in lines:
            threshold = max(
                SAME_LINE_MIN_CENTER_DELTA,
                SAME_LINE_HEIGHT_RATIO * max(float(line["anchor_height"]), height),
            )
            if abs(center_y - float(line["anchor_center_y"])) <= threshold:
                selected = line
                break
        if selected is None:
            selected = {
                "anchor_center_y": center_y,
                "anchor_height": height,
                "fragments": [],
            }
            lines.append(selected)
        selected["fragments"].append((fragment, x))
    ordered_lines: list[list[dict[str, Any]]] = []
    line_texts: list[str] = []
    for line in lines:
        ordered = [
            item[0] for item in sorted(
                line["fragments"],
                key=lambda value: (value[1], str(value[0].get("raw_observation_id"))),
            )
        ]
        ordered_lines.append(ordered)
        line_texts.append(INTRA_LINE_JOINER.join(str(item["text"]) for item in ordered))
    return LINE_JOINERS[line_joiner].join(line_texts), ordered_lines


def union_normalized_boxes(values: list[Any]) -> dict[str, float] | None:
    boxes: list[tuple[float, float, float, float]] = []
    for index, value in enumerate(values):
        try:
            boxes.append(normalized_box_metrics(value, f"aggregate_box[{index}]"))
        except VerificationError:
            return None
    if not boxes:
        return None
    left = min(value[0] for value in boxes)
    bottom = min(value[1] for value in boxes)
    right = max(value[0] + value[2] for value in boxes)
    top = max(value[1] + value[3] for value in boxes)
    return {"x": left, "y": bottom, "width": right - left, "height": top - bottom}


def build_exact_aggregate_observations(
    raw_text: list[dict[str, Any]], scans: list[ScanSpec],
    expected_fields: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return mapping observations plus hash-bound successful aggregates.

    Raw fragments consumed by one exact aggregate remain in ``raw_text`` with
    an explicit aggregate binding, but are removed from the canonical
    observation set so the same product pixels are not misclassified as extra
    pseudo-copy.
    """
    aggregates: list[dict[str, Any]] = []
    consumed_ids: set[str] = set()
    for field_id in sorted(expected_fields):
        field = expected_fields[field_id]
        if field.get("ocr_match_policy") != "ordered_line_aggregation_exact":
            continue
        region_id = field.get("region_id")
        candidates: list[tuple[ScanSpec, str, list[list[dict[str, Any]]], list[dict[str, Any]]]] = []
        for scan in scans:
            if (
                scan.scope != "projected_region_crop"
                or field_id not in scan.field_ids
                or not isinstance(region_id, str)
                or region_id not in scan.region_ids
            ):
                continue
            fragments = [item for item in raw_text if item.get("scan_id") == scan.scan_id]
            if not fragments:
                continue
            try:
                aggregate_text, ordered_lines = ordered_line_aggregation(
                    fragments, str(field.get("line_joiner")),
                )
            except VerificationError:
                continue
            if sha256_text(aggregate_text) == field.get("expected_text_sha256"):
                candidates.append((scan, aggregate_text, ordered_lines, fragments))
        # Multiple exact scans are not silently voted or selected.
        if len(candidates) != 1:
            continue
        scan, aggregate_text, ordered_lines, fragments = candidates[0]
        aggregate_id = f"RAW_{scan.scan_id}_AGG_{field_id}"
        component_ids = [
            str(fragment["raw_observation_id"])
            for line in ordered_lines for fragment in line
        ]
        component_set = set(component_ids)
        aggregate_full_box = union_normalized_boxes([
            item.get("full_master_bounding_box_normalized") for item in fragments
        ])
        aggregate_hash = sha256_text(aggregate_text)
        # Suppress equivalent whole-master detections only when exact text
        # bytes and physical pixels overlap a component or the full aggregate.
        for observation in raw_text:
            observation_id = str(observation.get("raw_observation_id"))
            equivalent = (
                observation_id in component_set
                or any(
                    observation.get("observed_hash") == component.get("observed_hash")
                    and intersection_over_min_area(
                        observation.get("full_master_bounding_box_normalized"),
                        component.get("full_master_bounding_box_normalized"),
                    ) >= 0.60
                    for component in fragments
                )
                or (
                    observation.get("observed_hash") == aggregate_hash
                    and intersection_over_min_area(
                        observation.get("full_master_bounding_box_normalized"), aggregate_full_box,
                    ) >= 0.60
                )
            )
            if equivalent:
                existing_owner = observation.get("consumed_by_aggregate_raw_observation_id")
                if isinstance(existing_owner, str) and existing_owner != aggregate_id:
                    raise VerificationError(
                        "one OCR fragment would be consumed by multiple aggregate fields"
                    )
                consumed_ids.add(observation_id)
                observation["consumed_by_aggregate_raw_observation_id"] = aggregate_id
        aggregates.append({
            "raw_observation_id": aggregate_id,
            "scan_id": scan.scan_id,
            "scan_scope": "projected_region_aggregate",
            "text": aggregate_text,
            "observed_hash": sha256_text(aggregate_text),
            "confidence": min(float(item.get("confidence", 0.0)) for item in fragments),
            "scan_bounding_box_normalized": union_normalized_boxes([
                item.get("scan_bounding_box_normalized") for item in fragments
            ]),
            "full_master_bounding_box_normalized": aggregate_full_box,
            "candidate_ids": [field_id],
            "region_ids": [region_id],
            "aggregation": {
                "policy": "ordered_line_aggregation_exact",
                "line_joiner": field.get("line_joiner"),
                "intra_line_joiner": "U+0020",
                "reading_order": "top_to_bottom_then_same_line_left_to_right",
                "same_line_min_center_delta": SAME_LINE_MIN_CENTER_DELTA,
                "same_line_height_ratio": SAME_LINE_HEIGHT_RATIO,
                "component_raw_observation_ids_by_line": [
                    [str(item["raw_observation_id"]) for item in line]
                    for line in ordered_lines
                ],
                "aggregate_text_sha256": aggregate_hash,
                "uses_language_correction": False,
            },
        })
    mapping_observations = [
        item for item in raw_text
        if str(item.get("raw_observation_id")) not in consumed_ids
    ] + aggregates
    return mapping_observations, aggregates


def exact_one_to_one_mapping(
    groups: list[list[dict[str, Any]]], expected: dict[str, dict[str, Any]], hash_key: str,
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    canonical: list[dict[str, Any]] = []
    for group in groups:
        representative = dict(choose_representative(group))
        candidate_ids: set[str] = set()
        for member in group:
            allowed = set(member.get("candidate_ids") or [])
            candidate_ids.update(
                identifier for identifier in allowed
                if expected.get(identifier, {}).get(hash_key) == member.get("observed_hash")
            )
        representative["candidate_ids"] = sorted(candidate_ids)
        representative["duplicate_scan_observation_ids"] = sorted(
            str(member["raw_observation_id"]) for member in group
            if member is not representative and member.get("raw_observation_id") != representative.get("raw_observation_id")
        )
        canonical.append(representative)
    candidates_by_expected: dict[str, list[dict[str, Any]]] = {identifier: [] for identifier in expected}
    for observation in canonical:
        if len(observation["candidate_ids"]) == 1:
            candidates_by_expected[observation["candidate_ids"][0]].append(observation)
    mapped: dict[str, dict[str, Any]] = {}
    for identifier, candidates in candidates_by_expected.items():
        if len(candidates) == 1:
            mapped[identifier] = candidates[0]
    return mapped, canonical


def projected_box_for_identifier(scans: Iterable[ScanSpec], identifier: str, kind: str) -> list[tuple[int, int, int, int]]:
    values: list[tuple[int, int, int, int]] = []
    attribute = "field_ids" if kind == "field" else "code_ids"
    for scan in scans:
        if scan.crop_box_px is not None and identifier in getattr(scan, attribute):
            values.append(scan.crop_box_px)
    return values


def point_box_contained_in_projected_region(
    normalized_box: Any, canvas_size: tuple[int, int], regions: list[tuple[int, int, int, int]],
) -> bool:
    if not isinstance(normalized_box, dict) or not regions:
        return False
    width, height = canvas_size
    observed = {
        "x": float(normalized_box["x"]), "y": float(normalized_box["y"]),
        "width": float(normalized_box["width"]), "height": float(normalized_box["height"]),
    }
    for left, top, right, bottom in regions:
        projected = {
            "x": left / width,
            "y": (height - bottom) / height,
            "width": (right - left) / width,
            "height": (bottom - top) / height,
        }
        if intersection_over_min_area(observed, projected) >= 0.95:
            return True
    return False


def discover_composition_receipts(root: Path) -> list[tuple[Path, dict[str, Any]]]:
    directory = root / "07_qa/composition_receipts"
    if not directory.is_dir():
        raise VerificationError("missing 07_qa/composition_receipts directory")
    records: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted(directory.rglob("*.json")):
        try:
            value = read_json(path)
        except (OSError, ValueError, json.JSONDecodeError, VerificationError):
            continue
        if value.get("schema_version") == "packaging-composition-receipt.v1":
            records.append((path, value))
    return records


def validate_composition_binding(
    root: Path, asset: dict[str, Any], receipt_path: Path, receipt: dict[str, Any],
    expected_fields: set[str], expected_codes: set[str], expected_graphics: set[str],
    text_fields: dict[str, dict[str, Any]], code_records: dict[str, dict[str, Any]],
    graphic_records: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], bool, list[str]]:
    reasons: list[str] = []
    if receipt.get("receipt_sha256") != canonical_hash(receipt, "receipt_sha256"):
        reasons.append("composition_receipt_self_hash_mismatch")
    if receipt.get("asset_id") != asset.get("asset_id") or receipt.get("view_id") != asset.get("view_id"):
        reasons.append("composition_receipt_asset_binding_mismatch")
    if receipt.get("output_file_sha256") != asset.get("file_sha256"):
        reasons.append("composition_receipt_output_hash_mismatch")
    if receipt.get("replay_status") != "byte_identical":
        reasons.append("composition_receipt_replay_not_byte_identical")
    if receipt.get("compositor_script_sha256") != sha256_file(COMPOSITOR_SCRIPT):
        reasons.append("composition_receipt_compositor_hash_mismatch")
    try:
        job_path = safe_path(root, receipt.get("composition_job_path"), "composition receipt job")
        if sha256_file(job_path) != receipt.get("composition_job_sha256"):
            raise VerificationError("composition job hash mismatch")
        job = read_json(job_path)
    except (OSError, ValueError, json.JSONDecodeError, VerificationError) as exc:
        raise VerificationError(f"{asset.get('view_id')}: cannot bind composition job: {exc}") from exc
    if job.get("schema_version") != "packaging-exact-copy-composition-job.v1":
        reasons.append("composition_job_schema_mismatch")
    if job.get("job_sha256") != canonical_hash(job, "job_sha256"):
        reasons.append("composition_job_self_hash_mismatch")
    if job.get("asset_id") != asset.get("asset_id") or job.get("view_id") != asset.get("view_id"):
        reasons.append("composition_job_asset_binding_mismatch")
    if job.get("output_path") != asset.get("file_path"):
        reasons.append("composition_job_output_path_mismatch")
    if job.get("receipt_path") != run_relative_locator(root, receipt_path, "composition receipt"):
        reasons.append("composition_job_receipt_path_mismatch")
    observed_fields: set[str] = set()
    observed_codes: set[str] = set()
    observed_graphics: set[str] = set()
    source_hashes: list[str] = []
    layers = job.get("layers")
    if not isinstance(layers, list) or not layers:
        reasons.append("composition_job_has_no_layers")
        layers = []
    for layer in layers:
        if not isinstance(layer, dict):
            reasons.append("composition_job_has_malformed_layer")
            continue
        source_hash = layer.get("source_sha256")
        if isinstance(source_hash, str):
            source_hashes.append(source_hash)
        else:
            reasons.append("composition_layer_source_hash_missing")
        for field_id in layer.get("field_ids") or []:
            observed_fields.add(field_id)
            if source_hash != text_fields.get(field_id, {}).get("authority_asset_sha256"):
                reasons.append(f"composition_field_source_mismatch:{field_id}")
        for code_id in layer.get("code_ids") or []:
            observed_codes.add(code_id)
            code = code_records.get(code_id, {})
            expected_source = code.get("authority_asset_sha256") or code.get("printed_symbol_asset_sha256")
            if source_hash != expected_source:
                reasons.append(f"composition_code_source_mismatch:{code_id}")
        for graphic_id in layer.get("graphic_ids") or []:
            observed_graphics.add(graphic_id)
            if source_hash != graphic_records.get(graphic_id, {}).get("asset_sha256"):
                reasons.append(f"composition_graphic_source_mismatch:{graphic_id}")
    if observed_fields != expected_fields:
        reasons.append("composition_visible_fields_mismatch")
    if observed_codes != expected_codes:
        reasons.append("composition_visible_codes_mismatch")
    if observed_graphics != expected_graphics:
        reasons.append("composition_visible_graphics_mismatch")
    if receipt.get("source_layer_sha256s") != source_hashes:
        reasons.append("composition_receipt_layer_hash_sequence_mismatch")
    if not reasons:
        try:
            compositor = load_bundled_module(COMPOSITOR_SCRIPT, "packaging_exact_copy_compositor_post_verify")
            replay_image, replay_hashes = compositor.render_job(root, job)
            replay_bytes = compositor.png_bytes(replay_image)
            asset_path = safe_path(root, asset.get("file_path"), "asset QA final master")
            if replay_bytes != asset_path.read_bytes() or replay_hashes != source_hashes:
                reasons.append("composition_replay_output_mismatch")
        except Exception as exc:
            reasons.append(f"composition_replay_failed:{type(exc).__name__}:{exc}")
    return job, not reasons, reasons


def build_graphic_comparison_receipt(
    root: Path, view_id: str, graphic_id: str, asset: dict[str, Any],
    job: dict[str, Any], receipt_path: Path, receipt: dict[str, Any],
    graphic: dict[str, Any], canvas_size: tuple[int, int],
    composition_passed: bool, replace: bool,
) -> tuple[str | None, str | None, bool, list[str]]:
    """Build a bundled, replay-bound graphic projection receipt.

    A handwritten similarity number has no authority.  ``1.0`` below means
    only that the installed compositor re-rendered the complete final asset to
    byte identity while this exact graphic source, projection geometry, and
    mask were locked in the immutable composition job.
    """
    root = root.resolve()
    reasons: list[str] = []
    layers = job.get("layers")
    matching_layers = [
        layer for layer in layers if isinstance(layer, dict)
        and graphic_id in (layer.get("graphic_ids") or [])
    ] if isinstance(layers, list) else []
    if not composition_passed:
        reasons.append("final_compositor_replay_not_verified")
    if len(matching_layers) != 1:
        reasons.append(f"graphic_layer_count_mismatch:{len(matching_layers)}")
        return None, None, False, reasons
    layer = matching_layers[0]
    layer_id = layer.get("layer_id")
    source_sha = graphic.get("asset_sha256")
    if not isinstance(layer_id, str) or not layer_id:
        reasons.append("graphic_layer_id_missing")
    if layer.get("source_sha256") != source_sha:
        reasons.append("graphic_layer_source_hash_mismatch")
    try:
        source_path = safe_path(root, layer.get("source_path"), f"{view_id}.{graphic_id}.source")
        mask_path = safe_path(root, layer.get("mask_path"), f"{view_id}.{graphic_id}.mask")
        if sha256_file(source_path) != source_sha:
            reasons.append("graphic_source_file_hash_mismatch")
        if sha256_file(mask_path) != layer.get("mask_sha256"):
            reasons.append("graphic_mask_file_hash_mismatch")
        parse_destination_box(layer, canvas_size, f"{view_id}.{graphic_id}.destination")
    except VerificationError as exc:
        reasons.append(f"graphic_layer_lock_invalid:{exc}")
        return None, None, False, reasons
    projection_model = layer.get("projection_model")
    if projection_model == "planar_homography":
        destination_geometry = {"destination_quad_px": layer.get("destination_quad_px")}
    else:
        destination_geometry = {"destination_box_px": layer.get("destination_box_px")}
    if reasons:
        return None, None, False, reasons
    comparison_path = root / "07_qa/graphic_comparisons" / f"{view_id}_{graphic_id}.json"
    if comparison_path.exists() and not replace:
        raise VerificationError(
            f"immutable graphic comparison candidate exists: {comparison_path}; "
            "use --replace-candidate to rerun"
        )
    composition_receipt_sha = sha256_file(receipt_path)
    composition_job_path = safe_path(
        root, receipt.get("composition_job_path"), f"{view_id}.{graphic_id}.composition_job",
    )
    graphic_receipt: dict[str, Any] = {
        "schema_version": "packaging-graphic-comparison-receipt.v1",
        "asset_id": asset.get("asset_id"), "view_id": view_id,
        "asset_file_sha256": asset.get("file_sha256"),
        "graphic_id": graphic_id,
        "source_graphic_sha256": source_sha,
        "comparison_adapter_path": ADAPTER_LOCATOR,
        "comparison_adapter_sha256": sha256_file(Path(__file__).resolve()),
        "composition_job_path": run_relative_locator(root, composition_job_path, f"{view_id}.{graphic_id}.composition_job"),
        "composition_job_sha256": sha256_file(composition_job_path),
        "composition_receipt_path": run_relative_locator(root, receipt_path, f"{view_id}.{graphic_id}.composition_receipt"),
        "composition_receipt_sha256": composition_receipt_sha,
        "layer_id": layer_id,
        "layer_source_lock": {
            "path": layer.get("source_path"),
            "sha256": layer.get("source_sha256"),
            "source_crop_box_px": layer.get("source_crop_box_px"),
        },
        "projection_lock": {
            "projection_model": projection_model,
            **destination_geometry,
        },
        "mask_lock": {
            "path": layer.get("mask_path"),
            "sha256": layer.get("mask_sha256"),
        },
        "final_compositor_replay": {
            "status": "byte_identical",
            "output_file_sha256": asset.get("file_sha256"),
            "compositor_script_sha256": sha256_file(COMPOSITOR_SCRIPT),
            "composition_receipt_replay_status": receipt.get("replay_status"),
        },
        "comparison_method": "bundled_composition_replay_source_projection_binding_v1",
        "deterministic_similarity": 1.0,
        "comparison_status": "matched",
        "receipt_sha256": None,
    }
    graphic_receipt["receipt_sha256"] = canonical_hash(graphic_receipt, "receipt_sha256")
    atomic_write_json(comparison_path, graphic_receipt)
    return run_relative_locator(root, comparison_path, f"{view_id}.{graphic_id}.graphic_comparison"), sha256_file(comparison_path), True, []


def produce_asset_evidence(
    root: Path, asset: dict[str, Any], view: dict[str, Any], job: dict[str, Any],
    receipt_path: Path, receipt: dict[str, Any], text_fields: dict[str, dict[str, Any]],
    code_records: dict[str, dict[str, Any]], graphic_records: dict[str, dict[str, Any]],
    languages: list[str], replace: bool, composition_passed: bool,
    composition_reasons: list[str],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, bool]]:
    view_id = str(view["view_id"])
    asset_id = str(asset["asset_id"])
    master_path = safe_path(root, asset.get("file_path"), f"asset {view_id} final master")
    asset_sha = sha256_file(master_path)
    if asset_sha != asset.get("file_sha256"):
        raise VerificationError(f"{view_id}: asset QA final-master hash is stale")
    canvas_size = verify_image(master_path)
    scans = make_scan_specs(root, view_id, master_path, job, canvas_size, replace)
    raw_results, engine_version = run_bundled_vision([scan.image_path for scan in scans], languages)
    expected_field_ids = strict_identifier_set(
        view.get("ocr_field_ids_visible"), f"{view_id}.ocr_field_ids_visible",
    )
    expected_code_ids = strict_identifier_set(
        view.get("code_ids_visible"), f"{view_id}.code_ids_visible",
    )
    expected_graphic_ids = strict_identifier_set(
        view.get("graphic_ids_visible"), f"{view_id}.graphic_ids_visible",
    )
    expected_fields = {identifier: text_fields[identifier] for identifier in expected_field_ids}
    expected_codes = {identifier: code_records[identifier] for identifier in expected_code_ids}
    validate_text_match_contract(expected_fields)

    raw_text: list[dict[str, Any]] = []
    raw_codes: list[dict[str, Any]] = []
    scan_records: list[dict[str, Any]] = []
    for scan, result in zip(scans, raw_results):
        scan_size = verify_image(scan.image_path)
        if Path(str(result.get("file_path", ""))).resolve() != scan.image_path.resolve():
            raise VerificationError(f"{scan.scan_id}: Vision result path binding mismatch")
        scan_sha = sha256_file(scan.image_path)
        allowed_fields = set(scan.field_ids) if scan.scope == "projected_region_crop" else expected_field_ids
        allowed_codes = set(scan.code_ids) if scan.scope == "projected_region_crop" else expected_code_ids
        scan_records.append({
            "scan_id": scan.scan_id, "scope": scan.scope,
            "image_path": scan.image_locator, "image_sha256": scan_sha,
            "pixel_dimensions": {"width": scan_size[0], "height": scan_size[1]},
            "crop_box_px_on_final_master": list(scan.crop_box_px) if scan.crop_box_px else None,
            "region_ids": list(scan.region_ids), "field_ids": list(scan.field_ids),
            "code_ids": list(scan.code_ids), "graphic_ids": list(scan.graphic_ids),
            "layer_ids": list(scan.layer_ids),
        })
        observations = result.get("text_observations")
        codes = result.get("code_observations")
        if not isinstance(observations, list) or not isinstance(codes, list):
            raise VerificationError(f"{scan.scan_id}: Vision result arrays are malformed")
        for index, item in enumerate(observations, start=1):
            if not isinstance(item, dict) or not isinstance(item.get("text"), str) or not item["text"]:
                continue
            observed_hash = sha256_text(item["text"])
            full_box = full_master_box(
                item.get("bounding_box_normalized"), scan, canvas_size, scan_size,
            )
            candidates = sorted(
                field_id for field_id in allowed_fields
                if text_fields[field_id].get("expected_text_sha256") == observed_hash
                and text_fields[field_id].get("ocr_match_policy") == "single_observation_exact"
                and full_box is not None
                and (
                    scan.scope == "projected_region_crop"
                    or point_box_contained_in_projected_region(
                        full_box, canvas_size, projected_box_for_identifier(scans, field_id, "field")
                    )
                )
            )
            raw_text.append({
                "raw_observation_id": f"RAW_{scan.scan_id}_TEXT_{index:04d}",
                "scan_id": scan.scan_id, "scan_scope": scan.scope,
                "text": item["text"], "observed_hash": observed_hash,
                "confidence": float(item.get("confidence", 0.0)),
                "scan_bounding_box_normalized": item.get("bounding_box_normalized"),
                "full_master_bounding_box_normalized": full_box,
                "candidate_ids": candidates,
                "region_ids": list(scan.region_ids),
            })
        for index, item in enumerate(codes, start=1):
            if not isinstance(item, dict):
                continue
            payload = item.get("payload")
            raw_symbology = item.get("symbology")
            if not isinstance(payload, str) or not payload or not isinstance(raw_symbology, str) or not raw_symbology:
                payload = payload if isinstance(payload, str) else ""
                raw_symbology = raw_symbology if isinstance(raw_symbology, str) else "unknown"
            canonical_observed = canonical_symbology(raw_symbology)
            observed_hash = sha256_text(payload)
            full_box = full_master_box(
                item.get("bounding_box_normalized"), scan, canvas_size, scan_size,
            )
            candidates = sorted(
                code_id for code_id in allowed_codes
                if str(code_records[code_id].get("expected_payload")) == payload
                and canonical_symbology(str(code_records[code_id].get("symbology"))) == canonical_observed
                and full_box is not None
                and (
                    scan.scope == "projected_region_crop"
                    or point_box_contained_in_projected_region(
                        full_box, canvas_size, projected_box_for_identifier(scans, code_id, "code")
                    )
                )
            )
            raw_codes.append({
                "raw_observation_id": f"RAW_{scan.scan_id}_CODE_{index:03d}",
                "scan_id": scan.scan_id, "scan_scope": scan.scope,
                "payload": payload, "observed_hash": observed_hash,
                "raw_symbology": raw_symbology,
                "canonical_symbology": canonical_observed,
                "scan_bounding_box_normalized": item.get("bounding_box_normalized"),
                "full_master_bounding_box_normalized": full_box,
                "candidate_ids": candidates,
                "region_ids": list(scan.region_ids),
            })

    field_expected = {
        field_id: {"expected_hash": record["expected_text_sha256"]}
        for field_id, record in expected_fields.items()
    }
    mapping_text, aggregate_observations = build_exact_aggregate_observations(
        raw_text, scans, expected_fields,
    )
    text_groups = cluster_physical_observations(mapping_text, ("text", "observed_hash"))
    mapped_fields, canonical_text = exact_one_to_one_mapping(
        text_groups, field_expected, "expected_hash",
    )
    observations: list[dict[str, Any]] = []
    for index, item in enumerate(canonical_text, start=1):
        mapped_ids = [field_id for field_id, candidate in mapped_fields.items() if candidate is item]
        field_id = mapped_ids[0] if len(mapped_ids) == 1 else None
        mapped = field_id is not None
        observation_record = {
            "observation_id": f"POST_{view_id}_TEXT_{index:04d}",
            "field_id": field_id,
            "text": item["text"], "text_sha256": item["observed_hash"],
            "confidence": item["confidence"],
            "region_id": item["region_ids"][0] if len(item["region_ids"]) == 1 else None,
            "full_master_bounding_box_normalized": item["full_master_bounding_box_normalized"],
            "source_scan_id": item["scan_id"],
            "raw_observation_ids": [item["raw_observation_id"], *item["duplicate_scan_observation_ids"]],
            "disposition": "mapped_to_expected_field" if mapped else "unresolved",
            "product_native": True if mapped else False,
            "review_status": "reviewed" if mapped else "review_required",
            "ocr_match_policy": expected_fields.get(field_id, {}).get("ocr_match_policy") if mapped else None,
            "mapping_basis": (
                "ordered_bbox_line_aggregation_exact_utf8_hash_one_to_one"
                if mapped and item.get("aggregation")
                else "single_observation_exact_utf8_hash_one_to_one"
                if mapped else "no_unique_exact_field_mapping"
            ),
        }
        if item.get("aggregation"):
            observation_record["aggregation"] = item["aggregation"]
        observations.append(observation_record)
        if mapped:
            mapped_fields[field_id] = observations[-1]
    field_results: list[dict[str, Any]] = []
    for field_id in sorted(expected_fields):
        observation = mapped_fields.get(field_id)
        expected_hash = expected_fields[field_id]["expected_text_sha256"]
        match = bool(observation and observation.get("text_sha256") == expected_hash)
        field_results.append({
            "field_id": field_id,
            "observation_id": observation.get("observation_id") if observation else None,
            "expected_text_sha256": expected_hash,
            "observed_text_sha256": observation.get("text_sha256") if observation else None,
            "match": match,
            "ocr_match_policy": expected_fields[field_id].get("ocr_match_policy"),
            "line_joiner": expected_fields[field_id].get("line_joiner"),
        })

    code_expected = {
        code_id: {"expected_hash": sha256_text(str(record.get("expected_payload")))}
        for code_id, record in expected_codes.items()
    }
    code_groups = cluster_physical_observations(raw_codes, ("payload", "canonical_symbology", "observed_hash"))
    mapped_codes, canonical_codes = exact_one_to_one_mapping(
        code_groups, code_expected, "expected_hash",
    )
    code_observations: list[dict[str, Any]] = []
    for index, item in enumerate(canonical_codes, start=1):
        mapped_ids = [code_id for code_id, candidate in mapped_codes.items() if candidate is item]
        code_id = mapped_ids[0] if len(mapped_ids) == 1 else None
        integrity, integrity_method = decoded_payload_integrity(item["canonical_symbology"], item["payload"])
        mapped = code_id is not None and integrity
        if code_id is not None and not integrity:
            mapped_codes.pop(code_id, None)
            code_id = None
        expected_symbology = expected_codes.get(code_id, {}).get("symbology") if code_id else None
        code_observations.append({
            "observation_id": f"POST_{view_id}_CODE_{index:03d}",
            "code_id": code_id,
            "symbology": expected_symbology if mapped else item["canonical_symbology"],
            "observed_symbology_raw": item["raw_symbology"],
            "symbology_mapping_id": "explicit_vision_aliases_v1",
            "payload": item["payload"], "payload_sha256": item["observed_hash"],
            "region_id": item["region_ids"][0] if len(item["region_ids"]) == 1 else None,
            "full_master_bounding_box_normalized": item["full_master_bounding_box_normalized"],
            "source_scan_id": item["scan_id"],
            "raw_observation_ids": [item["raw_observation_id"], *item["duplicate_scan_observation_ids"]],
            "decode_integrity_status": "passed" if integrity else "failed",
            "decode_integrity_method": integrity_method,
            "disposition": "mapped_to_expected_code" if mapped else "unresolved",
            "review_status": "reviewed" if mapped else "review_required",
        })
        if mapped and code_id:
            mapped_codes[code_id] = code_observations[-1]
    code_results: list[dict[str, Any]] = []
    for code_id in sorted(expected_codes):
        observation = mapped_codes.get(code_id)
        record = expected_codes[code_id]
        expected_payload = str(record.get("expected_payload"))
        expected_payload_hash = sha256_text(expected_payload)
        exact = bool(
            observation
            and observation.get("payload") == expected_payload
            and observation.get("symbology") == record.get("symbology")
            and observation.get("decode_integrity_status") == "passed"
        )
        geometry = bool(
            exact and point_box_contained_in_projected_region(
                observation.get("full_master_bounding_box_normalized"), canvas_size,
                projected_box_for_identifier(scans, code_id, "code"),
            )
        )
        decode_path: Path | None = None
        if exact:
            decode_path = root / "07_qa/post_ocr/code_decode_receipts" / view_id / f"{code_id}.json"
            if decode_path.exists() and not replace:
                raise VerificationError(
                    f"immutable code decode candidate exists: {decode_path}; use --replace-candidate to rerun"
                )
            decode_receipt: dict[str, Any] = {
                "schema_version": "packaging-post-code-decode-receipt.v1",
                "asset_id": asset_id, "view_id": view_id,
                "asset_file_sha256": asset_sha,
                "code_id": code_id,
                "engine_id": ENGINE_ID,
                "engine_script_path": ENGINE_SCRIPT_LOCATOR,
                "engine_script_sha256": sha256_file(VISION_SCRIPT),
                "observation_id": observation["observation_id"],
                "observed_symbology_raw": observation["observed_symbology_raw"],
                "canonical_symbology": observation["symbology"],
                "payload": observation["payload"],
                "payload_sha256": observation["payload_sha256"],
                "decode_integrity_status": observation["decode_integrity_status"],
                "decode_integrity_method": observation["decode_integrity_method"],
                "symbol_geometry_status": "matched" if geometry else "review_required",
                "receipt_sha256": None,
            }
            decode_receipt["receipt_sha256"] = canonical_hash(decode_receipt, "receipt_sha256")
            atomic_write_json(decode_path, decode_receipt)
        code_results.append({
            "code_id": code_id,
            "observation_id": observation.get("observation_id") if observation else None,
            "symbology": record.get("symbology"),
            "expected_payload_sha256": expected_payload_hash,
            "observed_payload_sha256": observation.get("payload_sha256") if observation else None,
            "payload_match": exact,
            "checksum_result": "passed" if exact else "failed",
            "symbol_geometry_status": "matched" if geometry else "review_required",
            "decode_receipt_path": run_relative_locator(root, decode_path, f"{view_id}.{code_id}.decode_receipt") if decode_path else None,
            "decode_receipt_sha256": sha256_file(decode_path) if decode_path else None,
        })

    composition_receipt_sha = sha256_file(receipt_path)
    graphic_results: list[dict[str, Any]] = []
    graphics_passed = True
    graphic_failure_reasons: list[str] = []
    for graphic_id in sorted(expected_graphic_ids):
        source_sha = graphic_records.get(graphic_id, {}).get("asset_sha256")
        path_value, hash_value, passed, graphic_reasons = build_graphic_comparison_receipt(
            root, view_id, graphic_id, asset, job, receipt_path, receipt,
            graphic_records[graphic_id], canvas_size, composition_passed, replace,
        )
        graphics_passed = graphics_passed and passed
        graphic_failure_reasons.extend(
            f"{graphic_id}:{reason}" for reason in graphic_reasons
        )
        graphic_results.append({
            "graphic_id": graphic_id,
            "source_graphic_sha256": source_sha,
            "comparison_status": "matched" if passed else "review_required",
            "comparison_receipt_path": path_value,
            "comparison_receipt_sha256": hash_value,
        })

    unresolved_text = [item for item in observations if item["disposition"] == "unresolved"]
    unresolved_codes = [item for item in code_observations if item["disposition"] == "unresolved"]
    fields_passed = (
        len(mapped_fields) == len(expected_fields)
        and all(item["match"] for item in field_results)
        and not unresolved_text
    )
    codes_passed = (
        len(mapped_codes) == len(expected_codes)
        and all(item["payload_match"] and item["symbol_geometry_status"] == "matched" for item in code_results)
        and not unresolved_codes
    )
    evidence: dict[str, Any] = {
        "schema_version": "packaging-post-ocr-evidence.v1",
        "asset_id": asset_id, "view_id": view_id,
        "asset_file_path": asset.get("file_path"), "asset_file_sha256": asset_sha,
        "engine_id": ENGINE_ID, "engine_version": engine_version,
        "engine_script_path": ENGINE_SCRIPT_LOCATOR,
        "engine_script_sha256": sha256_file(VISION_SCRIPT),
        "language_set": languages, "uses_language_correction": False,
        "review_status": "reviewed" if fields_passed and codes_passed else "review_required",
        "mapping_policy": "exact_utf8_single_or_fixed_bbox_line_aggregation_one_to_one_v2",
        "aggregation_order_contract": {
            "reading_order": "top_to_bottom_then_same_line_left_to_right",
            "same_line_min_center_delta": SAME_LINE_MIN_CENTER_DELTA,
            "same_line_height_ratio": SAME_LINE_HEIGHT_RATIO,
            "intra_line_joiner": "U+0020",
            "language_model_correction": "forbidden",
        },
        "scans": scan_records,
        "observations": observations,
        "code_observations": code_observations,
        "raw_scan_observations": {
            "text": raw_text, "codes": raw_codes,
        },
        "aggregate_observations": aggregate_observations,
        "unresolved_observation_ids": [
            item["observation_id"] for item in [*unresolved_text, *unresolved_codes]
        ],
        "missing_field_ids": sorted(expected_field_ids - set(mapped_fields)),
        "missing_code_ids": sorted(expected_code_ids - set(mapped_codes)),
    }
    evidence_path = root / "07_qa/post_ocr" / f"{view_id}.json"
    if evidence_path.exists() and not replace:
        raise VerificationError(
            f"immutable post OCR candidate exists: {evidence_path}; use --replace-candidate to rerun"
        )
    atomic_write_json(evidence_path, evidence)
    result = {
        "result_id": f"POST_{asset_id}",
        "asset_id": asset_id, "view_id": view_id,
        "asset_file_sha256": asset_sha,
        "composition_receipt_path": run_relative_locator(root, receipt_path, f"{view_id}.composition_receipt"),
        "composition_receipt_sha256": composition_receipt_sha,
        "post_ocr_evidence_path": run_relative_locator(root, evidence_path, f"{view_id}.post_ocr_evidence"),
        "post_ocr_evidence_sha256": sha256_file(evidence_path),
        "field_results": field_results,
        "code_results": code_results,
        "graphic_results": graphic_results,
        "verification_status": "passed" if fields_passed and codes_passed and composition_passed and graphics_passed else "failed",
        "failure_reasons": sorted({
            *composition_reasons,
            *graphic_failure_reasons,
            *(["unresolved_or_missing_exact_text"] if not fields_passed else []),
            *(["unresolved_missing_or_misplaced_code"] if not codes_passed else []),
            *(["graphic_comparison_evidence_missing_or_failed"] if not graphics_passed else []),
        }),
    }
    return result, evidence, {
        "copy": fields_passed,
        "codes": codes_passed,
        "composition": composition_passed,
        "graphics": graphics_passed,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", required=True, type=Path)
    parser.add_argument(
        "--language", action="append", default=[],
        help="Vision recognition language; repeat as needed (default: zh-Hans, en-US)",
    )
    parser.add_argument(
        "--output", default=DEFAULT_OUTPUT,
        help=f"Run-relative candidate JSON path (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--replace-candidate", action="store_true",
        help="Replace prior candidate crops/evidence; never edits the run manifest",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = args.run_root.resolve()
    try:
        if not root.is_dir():
            raise VerificationError(f"run root is not a directory: {root}")
        output_path = safe_path(root, args.output, "candidate output", must_exist=False)
        if output_path.exists() and not args.replace_candidate:
            raise VerificationError(
                f"immutable candidate already exists: {output_path}; use --replace-candidate to rerun"
            )
        if not VISION_SCRIPT.is_file() or not COMPOSITOR_SCRIPT.is_file():
            raise VerificationError("bundled OCR or compositor script is missing")
        manifest_path = root / "00_manifest/run_manifest.json"
        manifest = read_json(manifest_path)
        if manifest.get("schema_version") != "packaging-asset-pack-run.v3":
            raise VerificationError("run manifest schema_version is invalid")
        _, coverage = load_locked_manifest_json(
            root, manifest, "coverage_matrix", "coverage_matrix_sha256",
        )
        _, text_ssot = load_locked_manifest_json(root, manifest, "text_ssot", "text_ssot_sha256")
        _, code_manifest = load_locked_manifest_json(root, manifest, "code_manifest", "code_manifest_sha256")
        _, asset_qa = load_locked_manifest_json(root, manifest, "asset_qa", "asset_qa_sha256")
        _, graphic_manifest = load_locked_manifest_json(
            root, manifest, "logo_graphic_manifest", "logo_graphic_manifest_sha256",
        )
        views = coverage.get("views")
        assets = asset_qa.get("assets")
        fields = text_ssot.get("fields")
        codes = code_manifest.get("codes")
        graphics = graphic_manifest.get("graphics")
        if not all(isinstance(value, list) for value in (views, assets, fields, codes, graphics)):
            raise VerificationError("coverage/Text SSOT/code/graphic/asset arrays are malformed")
        required_view_records = [
            item for item in views
            if isinstance(item, dict) and item.get("required") is True
        ]
        required_views = {
            item["view_id"]: item for item in views
            if isinstance(item, dict) and item.get("required") is True
            and isinstance(item.get("view_id"), str) and bool(item.get("view_id"))
        }
        asset_by_view = {
            item["view_id"]: item for item in assets
            if isinstance(item, dict) and isinstance(item.get("view_id"), str) and bool(item.get("view_id"))
        }
        if not required_views:
            raise VerificationError("coverage contains no required views; an empty pack cannot be approved")
        if len(required_views) != len(required_view_records):
            raise VerificationError("coverage required view IDs must be present, non-empty, and unique")
        if len(asset_by_view) != len(assets):
            raise VerificationError("asset QA view IDs must be present, non-empty, and unique")
        asset_ids = [item.get("asset_id") for item in assets if isinstance(item, dict)]
        if (
            len(asset_ids) != len(assets)
            or not all(isinstance(value, str) and value for value in asset_ids)
            or len(set(asset_ids)) != len(asset_ids)
        ):
            raise VerificationError("asset QA asset IDs must be present, non-empty, and unique")
        if set(asset_by_view) != set(required_views):
            raise VerificationError("asset QA must exactly cover required coverage views before post verification")
        text_fields = {
            item["field_id"]: item for item in fields
            if isinstance(item, dict) and isinstance(item.get("field_id"), str) and bool(item.get("field_id"))
        }
        code_records = {
            item["code_id"]: item for item in codes
            if isinstance(item, dict) and isinstance(item.get("code_id"), str) and bool(item.get("code_id"))
        }
        graphic_records = {
            item["graphic_id"]: item for item in graphics
            if isinstance(item, dict) and isinstance(item.get("graphic_id"), str) and bool(item.get("graphic_id"))
        }
        if len(text_fields) != len(fields):
            raise VerificationError("Text SSOT field IDs must be present, non-empty, and unique")
        if len(code_records) != len(codes):
            raise VerificationError("code manifest IDs must be present, non-empty, and unique")
        if len(graphic_records) != len(graphics):
            raise VerificationError("graphic manifest IDs must be present, non-empty, and unique")
        validate_text_match_contract(text_fields)
        receipts = discover_composition_receipts(root)
        languages = args.language or ["zh-Hans", "en-US"]
        if any(not isinstance(value, str) or not value.strip() for value in languages):
            raise VerificationError("OCR languages must be non-empty strings")
        results: list[dict[str, Any]] = []
        statuses: list[dict[str, bool]] = []
        for view_id in sorted(required_views):
            view = required_views[view_id]
            asset = asset_by_view[view_id]
            expected_fields = strict_identifier_set(
                view.get("ocr_field_ids_visible"), f"{view_id}.ocr_field_ids_visible",
            )
            expected_codes = strict_identifier_set(
                view.get("code_ids_visible"), f"{view_id}.code_ids_visible",
            )
            expected_graphics = strict_identifier_set(
                view.get("graphic_ids_visible"), f"{view_id}.graphic_ids_visible",
            )
            if not expected_fields.issubset(text_fields):
                raise VerificationError(f"{view_id}: coverage references unknown Text SSOT fields")
            if not expected_codes.issubset(code_records):
                raise VerificationError(f"{view_id}: coverage references unknown codes")
            if not expected_graphics.issubset(graphic_records):
                raise VerificationError(f"{view_id}: coverage references unknown graphics")
            matches = [
                (path, receipt) for path, receipt in receipts
                if receipt.get("asset_id") == asset.get("asset_id")
                and receipt.get("view_id") == view_id
                and receipt.get("output_file_sha256") == asset.get("file_sha256")
            ]
            if len(matches) != 1:
                raise VerificationError(
                    f"{view_id}: expected exactly one composition receipt bound to this final master; found {len(matches)}"
                )
            receipt_path, receipt = matches[0]
            job, composition_passed, composition_reasons = validate_composition_binding(
                root, asset, receipt_path, receipt,
                expected_fields, expected_codes, expected_graphics,
                text_fields, code_records, graphic_records,
            )
            result, _, status = produce_asset_evidence(
                root, asset, view, job, receipt_path, receipt,
                text_fields, code_records, graphic_records,
                languages, args.replace_candidate, composition_passed, composition_reasons,
            )
            results.append(result)
            statuses.append(status)
        copy_passed = all(status["copy"] for status in statuses)
        codes_passed = all(status["codes"] for status in statuses)
        composition_passed = all(status["composition"] for status in statuses)
        graphics_passed = all(status["graphics"] for status in statuses)
        exact_passed = copy_passed and codes_passed and composition_passed and graphics_passed
        candidate: dict[str, Any] = {
            "schema_version": "packaging-post-composite-verification.v1",
            "candidate_provenance": {
                "adapter_path": "scripts/run_post_composite_verification.py",
                "adapter_sha256": sha256_file(Path(__file__).resolve()),
                "run_manifest_path": "00_manifest/run_manifest.json",
                "run_manifest_sha256": sha256_file(manifest_path),
                "engine_id": ENGINE_ID,
                "engine_script_path": ENGINE_SCRIPT_LOCATOR,
                "engine_script_sha256": sha256_file(VISION_SCRIPT),
                "uses_language_correction": False,
            },
            "asset_results": results,
            "copy_content_lock_status": "approved" if copy_passed else "failed",
            "label_artwork_lock_status": "approved" if composition_passed else "failed",
            "code_payload_lock_status": "approved" if codes_passed else "failed",
            "code_symbol_lock_status": "approved" if codes_passed else "failed",
            "logo_graphic_lock_status": "approved" if graphics_passed else "failed",
            "exact_copy_lock_status": "approved" if exact_passed else "failed",
            "candidate_status": "ready_for_manifest_binding" if exact_passed else "review_required",
        }
        atomic_write_json(output_path, candidate)
        print(json.dumps({
            "status": "PASS" if exact_passed else "REVIEW_REQUIRED",
            "candidate": run_relative_locator(root, output_path, "post verification candidate"),
            "candidate_sha256": sha256_file(output_path),
            "asset_count": len(results),
            "exact_copy_lock_status": candidate["exact_copy_lock_status"],
            "run_manifest_modified": False,
        }, ensure_ascii=False, sort_keys=True))
        return 0 if exact_passed else 2
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError, VerificationError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
