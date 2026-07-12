#!/usr/bin/env python3
"""Deterministically composite locked source artwork into one generated packaging base."""

from __future__ import annotations

import argparse
import copy
import hashlib
import io
import json
import os
from pathlib import Path
from typing import Any

from PIL import Image


SUPPORTED_PROJECTION_MODELS = {
    "source_pixel_preservation", "planar_rectangle", "planar_homography",
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_hash(value: dict[str, Any]) -> str:
    payload = copy.deepcopy(value)
    payload.pop("receipt_sha256", None)
    payload.pop("job_sha256", None)
    return sha256_bytes(json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8"))


def resolve_locked_file(root: Path, locator: Any, expected_hash: Any, label: str) -> Path:
    if not isinstance(locator, str) or not locator:
        raise ValueError(f"{label}: path must be non-empty")
    relative = Path(locator)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"{label}: path must be run-relative and cannot contain '..'")
    path = (root.resolve() / relative).resolve()
    path.relative_to(root.resolve())
    if not path.is_file():
        raise ValueError(f"{label}: file is missing")
    if expected_hash != sha256_file(path):
        raise ValueError(f"{label}: SHA-256 mismatch")
    return path


def parse_box(value: Any, label: str, image_size: tuple[int, int]) -> tuple[int, int, int, int]:
    if not isinstance(value, list) or len(value) != 4 or not all(isinstance(item, int) for item in value):
        raise ValueError(f"{label}: expected [left, top, right, bottom] integer pixels")
    left, top, right, bottom = value
    if left < 0 or top < 0 or right <= left or bottom <= top or right > image_size[0] or bottom > image_size[1]:
        raise ValueError(f"{label}: box is empty or outside the image")
    return left, top, right, bottom


def solve_linear(matrix: list[list[float]], vector: list[float]) -> list[float]:
    size = len(vector)
    augmented = [list(row) + [vector[index]] for index, row in enumerate(matrix)]
    for column in range(size):
        pivot = max(range(column, size), key=lambda row: abs(augmented[row][column]))
        if abs(augmented[pivot][column]) < 1e-12:
            raise ValueError("planar_homography destination quad is singular")
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        divisor = augmented[column][column]
        augmented[column] = [value / divisor for value in augmented[column]]
        for row in range(size):
            if row == column:
                continue
            factor = augmented[row][column]
            augmented[row] = [
                augmented[row][index] - factor * augmented[column][index]
                for index in range(size + 1)
            ]
    return [augmented[index][-1] for index in range(size)]


def perspective_coefficients(
    destination_quad: list[tuple[float, float]], source_size: tuple[int, int],
) -> tuple[float, ...]:
    source_quad = [
        (0.0, 0.0), (float(source_size[0]), 0.0),
        (float(source_size[0]), float(source_size[1])), (0.0, float(source_size[1])),
    ]
    matrix: list[list[float]] = []
    vector: list[float] = []
    for (x, y), (u, v) in zip(destination_quad, source_quad):
        matrix.append([x, y, 1.0, 0.0, 0.0, 0.0, -x * u, -y * u]); vector.append(u)
        matrix.append([0.0, 0.0, 0.0, x, y, 1.0, -x * v, -y * v]); vector.append(v)
    return tuple(solve_linear(matrix, vector))


def parse_quad(value: Any, label: str, canvas_size: tuple[int, int]) -> list[tuple[float, float]]:
    if not isinstance(value, list) or len(value) != 4:
        raise ValueError(f"{label}: expected four [x,y] points")
    points: list[tuple[float, float]] = []
    for item in value:
        if not isinstance(item, list) or len(item) != 2 or not all(isinstance(axis, (int, float)) for axis in item):
            raise ValueError(f"{label}: every point must be numeric [x,y]")
        point = (float(item[0]), float(item[1]))
        if point[0] < 0 or point[1] < 0 or point[0] > canvas_size[0] or point[1] > canvas_size[1]:
            raise ValueError(f"{label}: point lies outside canvas")
        points.append(point)
    area = abs(sum(
        points[index][0] * points[(index + 1) % 4][1]
        - points[(index + 1) % 4][0] * points[index][1]
        for index in range(4)
    )) / 2.0
    if area < 1.0:
        raise ValueError(f"{label}: quad is empty or degenerate")
    return points


def load_rgba(path: Path) -> Image.Image:
    with Image.open(path) as probe:
        probe.verify()
    with Image.open(path) as decoded:
        decoded.load()
        return decoded.convert("RGBA")


def load_mask(path: Path) -> Image.Image:
    with Image.open(path) as probe:
        probe.verify()
    with Image.open(path) as decoded:
        decoded.load()
        if "A" in decoded.getbands():
            alpha = decoded.getchannel("A")
            if alpha.getextrema() != (255, 255):
                return alpha
        return decoded.convert("L")


def render_job(root: Path, job: dict[str, Any]) -> tuple[Image.Image, list[str]]:
    base_lock = job.get("base_asset")
    if not isinstance(base_lock, dict):
        raise ValueError("base_asset lock is required")
    base_path = resolve_locked_file(
        root, base_lock.get("path"), base_lock.get("file_sha256"), "base_asset"
    )
    canvas = load_rgba(base_path)
    if canvas.width * 9 != canvas.height * 16:
        raise ValueError("base_asset must be exact horizontal 16:9")
    layers = job.get("layers")
    if not isinstance(layers, list) or not layers:
        raise ValueError("layers must be a non-empty array")
    source_hashes: list[str] = []
    seen_ids: set[str] = set()
    for index, layer in enumerate(layers):
        label = f"layers[{index}]"
        if not isinstance(layer, dict):
            raise ValueError(f"{label}: must be an object")
        layer_id = layer.get("layer_id")
        if not isinstance(layer_id, str) or not layer_id or layer_id in seen_ids:
            raise ValueError(f"{label}: layer_id must be unique")
        seen_ids.add(layer_id)
        method = layer.get("projection_model")
        if method not in SUPPORTED_PROJECTION_MODELS:
            raise ValueError(f"{label}: unsupported projection_model; fail closed")
        source_path = resolve_locked_file(
            root, layer.get("source_path"), layer.get("source_sha256"), f"{label}.source"
        )
        source_hashes.append(sha256_file(source_path))
        source = load_rgba(source_path)
        crop_box = parse_box(layer.get("source_crop_box_px"), f"{label}.source_crop_box_px", source.size)
        patch = source.crop(crop_box)
        mask_path = resolve_locked_file(
            root, layer.get("mask_path"), layer.get("mask_sha256"), f"{label}.mask"
        )
        mask = load_mask(mask_path)
        if method == "planar_homography":
            if mask.size != patch.size:
                raise ValueError(f"{label}: homography mask must match the locked source crop")
            quad = parse_quad(layer.get("destination_quad_px"), f"{label}.destination_quad_px", canvas.size)
            coefficients = perspective_coefficients(quad, patch.size)
            warped_patch = patch.transform(
                canvas.size, Image.Transform.PERSPECTIVE, coefficients,
                resample=Image.Resampling.BICUBIC, fillcolor=(0, 0, 0, 0),
            )
            warped_mask = mask.transform(
                canvas.size, Image.Transform.PERSPECTIVE, coefficients,
                resample=Image.Resampling.NEAREST, fillcolor=0,
            )
            canvas.paste(warped_patch, (0, 0), warped_mask)
        else:
            destination_box = parse_box(layer.get("destination_box_px"), f"{label}.destination_box_px", canvas.size)
            target_size = (destination_box[2] - destination_box[0], destination_box[3] - destination_box[1])
            if method == "source_pixel_preservation" and patch.size != target_size:
                raise ValueError(f"{label}: source_pixel_preservation forbids resizing")
            if patch.size != target_size:
                patch = patch.resize(target_size, Image.Resampling.LANCZOS)
            if mask.size != target_size:
                mask = mask.resize(target_size, Image.Resampling.NEAREST)
            canvas.alpha_composite(patch, (destination_box[0], destination_box[1])) if mask.getextrema() == (255, 255) else canvas.paste(
                patch, (destination_box[0], destination_box[1]), mask
            )
    return canvas, source_hashes


def png_bytes(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.convert("RGB").save(buffer, format="PNG", optimize=False, compress_level=6)
    return buffer.getvalue()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", required=True, type=Path)
    parser.add_argument("--job", required=True, type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = args.run_root.resolve()
    try:
        job_path = args.job.resolve()
        job_path.relative_to(root)
        job = json.loads(job_path.read_text(encoding="utf-8"))
        if not isinstance(job, dict) or job.get("schema_version") != "packaging-exact-copy-composition-job.v1":
            raise ValueError("composition job schema_version is invalid")
        if job.get("job_sha256") != canonical_hash(job):
            raise ValueError("composition job self hash is missing or stale")
        first, source_hashes = render_job(root, job)
        second, second_source_hashes = render_job(root, job)
        first_bytes = png_bytes(first)
        second_bytes = png_bytes(second)
        if first_bytes != second_bytes or source_hashes != second_source_hashes:
            raise ValueError("deterministic replay produced different bytes")
        output_value = job.get("output_path")
        receipt_value = job.get("receipt_path")
        if not isinstance(output_value, str) or not isinstance(receipt_value, str):
            raise ValueError("output_path and receipt_path are required")
        output = (root / Path(output_value)).resolve()
        receipt_path = (root / Path(receipt_value)).resolve()
        output.relative_to(root)
        receipt_path.relative_to(root)
        if Path(output_value).is_absolute() or ".." in Path(output_value).parts:
            raise ValueError("output_path must be run-relative")
        if Path(receipt_value).is_absolute() or ".." in Path(receipt_value).parts:
            raise ValueError("receipt_path must be run-relative")
        if output.exists() or receipt_path.exists():
            raise ValueError("immutable output or receipt already exists")
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = output.with_name(output.name + ".tmp")
        temporary.write_bytes(first_bytes)
        os.replace(temporary, output)
        receipt: dict[str, Any] = {
            "schema_version": "packaging-composition-receipt.v1",
            "asset_id": job.get("asset_id"), "view_id": job.get("view_id"),
            "output_file_sha256": sha256_file(output),
            "prompt_sha256": job.get("prompt_sha256"),
            "composition_plan_id": job.get("composition_plan_id"),
            "composition_plan_sha256": job.get("composition_plan_sha256"),
            "exact_copy_bundle_sha256": job.get("exact_copy_bundle_sha256"),
            "source_layer_sha256s": source_hashes,
            "compositor_script_sha256": sha256_file(Path(__file__).resolve()),
            "composition_job_path": job_path.relative_to(root).as_posix(),
            "composition_job_sha256": sha256_file(job_path),
            "replay_status": "byte_identical",
            "receipt_sha256": None,
        }
        receipt["receipt_sha256"] = canonical_hash(receipt)
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        receipt_path.write_text(
            json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        print(json.dumps({
            "status": "PASS", "output": str(output), "output_sha256": sha256_file(output),
            "receipt": str(receipt_path), "receipt_sha256": sha256_file(receipt_path),
        }, ensure_ascii=False, sort_keys=True))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
