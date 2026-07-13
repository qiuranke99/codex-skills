#!/usr/bin/env python3
"""Run mandatory whole-product OCR before packaging prompt compilation.

The output is an observation ledger, not an exact-copy SSOT. A later
reconciliation step must bind authoritative fields, graphics, and code payloads.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
from macos_vision_adapter import VisionAdapterError, run_macos_vision as run_strict_macos_vision

try:
    from PIL import Image
except ImportError:  # pragma: no cover - exercised by capability gate
    Image = None  # type: ignore[assignment]


SKILL_DIR = Path(__file__).resolve().parents[1]
VISION_SCRIPT = SKILL_DIR / "scripts/macos_vision_ocr.swift"
PREFLIGHT_ADAPTER_PATH = "scripts/run_ocr_preflight.py"


class PreflightError(RuntimeError):
    def __init__(self, message: str, exit_code: int = 1) -> None:
        super().__init__(message)
        self.exit_code = exit_code


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_ledger_hash(value: dict[str, Any]) -> str:
    payload = dict(value)
    payload.pop("ledger_semantic_sha256", None)
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def engine_adapter_binding(engine: str) -> tuple[str, str]:
    if engine == "macos_vision":
        if not VISION_SCRIPT.is_file():
            raise PreflightError("blocked_ocr_capability: bundled macOS Vision adapter is missing", 4)
        return "scripts/macos_vision_ocr.swift", sha256_file(VISION_SCRIPT)
    if engine == "tesseract":
        executable = shutil.which("tesseract")
        if not executable:
            raise PreflightError("blocked_ocr_capability: Tesseract executable is unavailable", 4)
        path = Path(executable).resolve()
        return str(path), sha256_file(path)
    raise PreflightError(f"blocked_ocr_capability: unsupported OCR engine {engine}", 4)


def image_dimensions(path: Path) -> tuple[int, int]:
    if Image is None:
        raise PreflightError("Pillow is required to verify source image pixels", 4)
    try:
        with Image.open(path) as probe:
            width, height = probe.size
            probe.verify()
        with Image.open(path) as decoded:
            decoded.load()
    except Exception as exc:  # Pillow raises several format-specific exceptions
        raise PreflightError(f"source image is not fully decodable: {path}: {exc}", 3) from exc
    if width < 1 or height < 1:
        raise PreflightError(f"source image has invalid dimensions: {path}", 3)
    return width, height


def stable_source_ids(paths: list[Path]) -> list[str]:
    used: set[str] = set()
    values: list[str] = []
    for index, path in enumerate(paths, start=1):
        token = "".join(ch if ch.isalnum() else "_" for ch in path.stem.upper()).strip("_")
        token = token or f"SOURCE_{index:03d}"
        candidate = f"SRC_{token}"
        if candidate in used:
            candidate = f"{candidate}_{index:03d}"
        used.add(candidate)
        values.append(candidate)
    return values


def select_engine(requested: str) -> str:
    if requested != "auto":
        return requested
    if platform.system() == "Darwin" and shutil.which("swift") and VISION_SCRIPT.is_file():
        return "macos_vision"
    if shutil.which("tesseract"):
        return "tesseract"
    raise PreflightError(
        "blocked_ocr_capability: no macOS Vision adapter or Tesseract executable is available",
        4,
    )


def run_macos_vision(paths: list[Path], languages: list[str]) -> tuple[list[dict[str, Any]], str]:
    try:
        return run_strict_macos_vision(VISION_SCRIPT, paths, languages)
    except VisionAdapterError as exc:
        raise PreflightError(str(exc), 4) from exc


def tesseract_languages_available(executable: str) -> set[str]:
    result = subprocess.run([executable, "--list-langs"], check=False, capture_output=True, text=True)
    if result.returncode != 0:
        raise PreflightError(f"Tesseract language query failed: {result.stderr.strip()}", 4)
    return {line.strip() for line in result.stdout.splitlines()[1:] if line.strip()}


def run_tesseract(
    paths: list[Path], language_spec: str
) -> tuple[list[dict[str, Any]], str]:
    executable = shutil.which("tesseract")
    if not executable:
        raise PreflightError("blocked_ocr_capability: Tesseract executable is unavailable", 4)
    required = set(language_spec.split("+"))
    missing = sorted(required - tesseract_languages_available(executable))
    if missing:
        raise PreflightError(
            "blocked_required_language_support: missing Tesseract languages " + ", ".join(missing),
            4,
        )
    version_result = subprocess.run([executable, "--version"], check=False, capture_output=True, text=True)
    version = version_result.stdout.splitlines()[0].strip() if version_result.stdout else "unknown"
    records: list[dict[str, Any]] = []
    for path in paths:
        width, height = image_dimensions(path)
        observations: list[dict[str, Any]] = []
        for psm in (11, 6):
            result = subprocess.run(
                [executable, str(path), "stdout", "-l", language_spec, "--psm", str(psm), "tsv"],
                check=False,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                raise PreflightError(f"Tesseract OCR failed for {path}: {result.stderr.strip()}", 4)
            reader = csv.DictReader(io.StringIO(result.stdout), delimiter="\t")
            for row in reader:
                text = (row.get("text") or "").strip()
                try:
                    confidence = float(row.get("conf") or -1)
                    left, top = int(row.get("left") or 0), int(row.get("top") or 0)
                    box_width, box_height = int(row.get("width") or 0), int(row.get("height") or 0)
                except ValueError:
                    continue
                if not text or confidence < 0 or box_width <= 0 or box_height <= 0:
                    continue
                observations.append(
                    {
                        "text": text,
                        "confidence": max(0.0, min(1.0, confidence / 100.0)),
                        "bounding_box_normalized": {
                            "x": left / width,
                            "y": max(0.0, 1.0 - ((top + box_height) / height)),
                            "width": box_width / width,
                            "height": box_height / height,
                        },
                        "scope": "whole_product",
                        "region_id": None,
                        "visibility_mode": "unclassified",
                        "pass_psm": psm,
                    }
                )
        records.append(
            {
                "file_path": str(path),
                "width": width,
                "height": height,
                "coordinate_origin": "bottom_left_normalized",
                "text_observations": observations,
                "code_observations": [],
            }
        )
    return records, version


def normalize_records(
    paths: list[Path], source_ids: list[str], raw: list[dict[str, Any]], engine: str,
    engine_version: str, languages: list[str], engine_adapter_path: str,
    engine_adapter_sha256: str,
) -> dict[str, Any]:
    by_path = {str(Path(item["file_path"]).resolve()): item for item in raw}
    source_records: list[dict[str, Any]] = []
    for source_id, path in zip(source_ids, paths):
        width, height = image_dimensions(path)
        item = by_path.get(str(path.resolve()))
        if item is None:
            raise PreflightError(f"OCR engine omitted source: {path}", 4)
        text_items: list[dict[str, Any]] = []
        for index, observation in enumerate(item.get("text_observations", []), start=1):
            text_items.append(
                {
                    "observation_id": f"{source_id}_TEXT_{index:04d}",
                    "text": str(observation.get("text", "")),
                    "confidence": float(observation.get("confidence", 0.0)),
                    "bounding_box_normalized": observation.get("bounding_box_normalized"),
                    "scope": "whole_product",
                    "region_id": None,
                    "visibility_mode": "unclassified",
                    "disposition": {
                        "status": "unresolved",
                        "review_status": "review_required",
                        "reviewer_id": None,
                        "field_id": None,
                        "evidence_note": "Whole-product OCR discovery must be reconciled before exact-copy generation.",
                    },
                }
            )
        code_items: list[dict[str, Any]] = []
        for index, observation in enumerate(item.get("code_observations", []), start=1):
            code_items.append(
                {
                    "code_id": f"{source_id}_CODE_{index:03d}",
                    "symbology": str(observation.get("symbology", "unknown")),
                    "payload": observation.get("payload"),
                    "bounding_box_normalized": observation.get("bounding_box_normalized"),
                    "disposition": {
                        "status": "unresolved",
                        "review_status": "review_required",
                        "reviewer_id": None,
                        "manifest_code_id": None,
                        "evidence_note": "Decoded code discovery must be reconciled before exact-copy generation.",
                    },
                }
            )
        source_records.append(
            {
                "source_id": source_id,
                "file_path": str(path.resolve()),
                "file_sha256": sha256_file(path),
                "pixel_dimensions": {"width": width, "height": height},
                "whole_product_ocr_passes": [
                    {
                        "pass_id": f"{source_id}_FULL_01",
                        "scope": "whole_product",
                        "engine_id": engine,
                        "engine_version": engine_version,
                        "preflight_adapter_path": PREFLIGHT_ADAPTER_PATH,
                        "preflight_adapter_sha256": sha256_file(Path(__file__).resolve()),
                        "engine_adapter_path": engine_adapter_path,
                        "engine_adapter_sha256": engine_adapter_sha256,
                        "source_sha256": sha256_file(path),
                        "language_set": languages,
                        "uses_language_correction": False,
                        "observation_count": len(text_items),
                    }
                ],
                "region_ocr_passes": [],
                "text_observations": text_items,
                "code_observations": code_items,
                "ocr_review_status": "pending",
                "zero_detection_review_status": None,
            }
        )
    ledger: dict[str, Any] = {
        "schema_version": "packaging-ocr-observations.v1",
        "engine": engine,
        "engine_version": engine_version,
        "preflight_adapter_path": PREFLIGHT_ADAPTER_PATH,
        "preflight_adapter_sha256": sha256_file(Path(__file__).resolve()),
        "engine_adapter_path": engine_adapter_path,
        "engine_adapter_sha256": engine_adapter_sha256,
        "language_set": languages,
        "uses_language_correction": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_records": source_records,
        "preflight_status": "observations_ready",
        "ledger_semantic_sha256": None,
    }
    ledger["ledger_semantic_sha256"] = canonical_ledger_hash(ledger)
    return ledger


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", action="append", required=True, type=Path, help="Original product image; repeat for every source")
    parser.add_argument("--output", required=True, type=Path, help="Output ocr_observations.json")
    parser.add_argument("--engine", choices=["auto", "macos_vision", "tesseract"], default="auto")
    parser.add_argument("--language", action="append", default=[], help="Vision language code; defaults to zh-Hans and en-US")
    parser.add_argument("--tesseract-languages", default="chi_sim+eng")
    parser.add_argument("--require-code-detection", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    paths = [path.resolve() for path in args.source]
    for path in paths:
        if not path.is_file():
            print(f"ERROR: source file does not exist: {path}")
            return 3
        image_dimensions(path)
    languages = args.language or ["zh-Hans", "en-US"]
    try:
        engine = select_engine(args.engine)
        if engine == "macos_vision":
            raw, version = run_macos_vision(paths, languages)
        else:
            raw, version = run_tesseract(paths, args.tesseract_languages)
        engine_adapter_path, engine_adapter_sha256 = engine_adapter_binding(engine)
        ledger = normalize_records(
            paths, stable_source_ids(paths), raw, engine, version, languages,
            engine_adapter_path, engine_adapter_sha256,
        )
        if args.require_code_detection and not any(record["code_observations"] for record in ledger["source_records"]):
            raise PreflightError(
                "blocked_barcode_qr_decode_capability: no code payload was decoded from the supplied sources",
                4,
            )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(ledger, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({
            "status": "observations_ready",
            "engine": engine,
            "source_count": len(paths),
            "text_observation_count": sum(len(item["text_observations"]) for item in ledger["source_records"]),
            "code_observation_count": sum(len(item["code_observations"]) for item in ledger["source_records"]),
            "output": str(args.output),
            "sha256": sha256_file(args.output),
        }, ensure_ascii=False, sort_keys=True))
        return 0
    except PreflightError as exc:
        print(f"ERROR: {exc}")
        return exc.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
