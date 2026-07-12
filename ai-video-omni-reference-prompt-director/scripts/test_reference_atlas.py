#!/usr/bin/env python3
"""Positive and adversarial tests for the deterministic common-raster atlas."""

from __future__ import annotations

import copy
import hashlib
import tempfile
from pathlib import Path
from typing import Any, Callable

from PIL import Image

import build_reference_atlas as atlas


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_image(path: Path, image_format: str, size: tuple[int, int], color: tuple[int, int, int]) -> None:
    image = Image.new("RGB", size, color)
    options: dict[str, Any] = {}
    if image_format in {"JPEG", "WEBP"}:
        options.update({"quality": 92})
    image.save(path, format=image_format, **options)


def make_spec(root: Path) -> dict[str, Any]:
    sources = []
    cases = (
        ("CHARACTER", "character.png", "PNG", (256, 300), (70, 90, 110), "identity"),
        ("PRODUCT", "product.jpg", "JPEG", (320, 256), (130, 110, 80), "product_geometry"),
        ("SCENE", "scene.webp", "WEBP", (280, 270), (45, 120, 75), "scene_canon"),
    )
    for artifact_id, name, image_format, size, color, role in cases:
        path = root / name
        write_image(path, image_format, size, color)
        sources.append({
            "artifact_id": artifact_id,
            "file_path": name,
            "file_sha256": digest(path),
            "control_roles": [role],
            "control_role": role,
        })
    return {
        "schema_version": atlas.ATLAS_SPEC_VERSION,
        "atlas_id": "ATLAS_GU001",
        "generation_unit_id": "GU001",
        "layout_columns": 2,
        "background_rgb": [3, 5, 7],
        "minimum_panel_width_pixels": 256,
        "minimum_panel_height_pixels": 256,
        "legibility_policy": atlas.ATLAS_LEGIBILITY_POLICY,
        "source_decode_policy": atlas.SOURCE_DECODE_POLICY,
        "output_encode_policy": atlas.OUTPUT_ENCODE_POLICY,
        "layout_policy": atlas.ATLAS_LAYOUT_POLICY,
        "output_codec": atlas.ATLAS_CODEC,
        "sources": sources,
    }


def expect_error(name: str, action: Callable[[], Any], needle: str) -> None:
    try:
        action()
    except (OSError, ValueError, TypeError) as exc:
        if needle not in str(exc):
            raise AssertionError(f"{name}: expected {needle!r}, got {exc!r}") from exc
    else:
        raise AssertionError(f"{name}: expected failure")


def main() -> int:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        spec = make_spec(root)
        first_bytes, first_receipt = atlas.build_from_spec(root, spec)
        second_bytes, second_receipt = atlas.build_from_spec(root, copy.deepcopy(spec))
        if first_bytes != second_bytes or first_receipt != second_receipt:
            raise AssertionError("identical sources/spec/runtime must rebuild byte-identically")
        if first_receipt["codec"] != "PNG_RGB8" or first_receipt["media_type"] != "image/png":
            raise AssertionError("atlas output is not declared as provider-usable RGB8 PNG")
        with Image.open(root / "character.png") as source_image:
            if source_image.size != (256, 300):
                raise AssertionError("source fixture changed unexpectedly")
        atlas_path = root / "atlas.png"
        atlas_path.write_bytes(first_bytes)
        with Image.open(atlas_path) as output:
            if output.format != "PNG" or output.mode != "RGB" or output.size != (640, 600):
                raise AssertionError(f"unexpected atlas image properties: {output.format}, {output.mode}, {output.size}")
            if output.info:
                raise AssertionError(f"atlas output must contain no variable metadata: {output.info}")
        panels = first_receipt["panels"]
        if [(item["width"], item["height"]) for item in panels] != [(256, 300), (320, 256), (280, 270)]:
            raise AssertionError("native panel dimensions were not preserved")
        if any((item["cell_width"], item["cell_height"]) != (320, 300) for item in panels):
            raise AssertionError("mixed native sizes did not use the frozen max-cell padding policy")
        if [item["source_codec"] for item in panels] != ["PNG", "JPEG", "WEBP"]:
            raise AssertionError("common raster codec evidence missing from receipt")
        if first_receipt["decoder_runtime"]["implementation"] != "Pillow":
            raise AssertionError("decoder implementation/version was not sealed")
        if first_receipt["encoder_runtime"]["parameters"] != atlas.PNG_ENCODER_PARAMETERS:
            raise AssertionError("fixed PNG encoder parameters were not sealed")

        tampered = copy.deepcopy(spec)
        tampered["sources"][0]["file_sha256"] = "0" * 64
        expect_error("source hash tamper", lambda: atlas.build_from_spec(root, tampered), "file hash mismatch")

        too_small = root / "small.png"
        write_image(too_small, "PNG", (255, 256), (1, 2, 3))
        small_spec = copy.deepcopy(spec)
        small_spec["sources"][0].update({"file_path": too_small.name, "file_sha256": digest(too_small)})
        expect_error("native legibility minimum", lambda: atlas.build_from_spec(root, small_spec), "below the frozen legibility threshold")

        animated = root / "animated.webp"
        Image.new("RGB", (256, 256), (1, 2, 3)).save(
            animated,
            format="WEBP",
            save_all=True,
            append_images=[Image.new("RGB", (256, 256), (240, 5, 200))],
            duration=[100, 100],
            loop=0,
            lossless=True,
        )
        animated_spec = copy.deepcopy(spec)
        animated_spec["sources"][2].update({"file_path": animated.name, "file_sha256": digest(animated)})
        expect_error("animated source", lambda: atlas.build_from_spec(root, animated_spec), "animated or multi-frame")

        ppm = root / "legacy.ppm"
        ppm.write_bytes(b"P6\n256 256\n255\n" + bytes((1, 2, 3)) * 256 * 256)
        unsupported = copy.deepcopy(spec)
        unsupported["sources"][0].update({"file_path": ppm.name, "file_sha256": digest(ppm)})
        expect_error("unsupported codec", lambda: atlas.build_from_spec(root, unsupported), "expected PNG, JPEG, or WebP")

        one_source = copy.deepcopy(spec)
        one_source["sources"] = one_source["sources"][:1]
        expect_error("single-source group", lambda: atlas.build_from_spec(root, one_source), "at least two sources")

        original_version = atlas.PIL.__version__
        try:
            atlas.PIL.__version__ = original_version + "-drift"
            drift_bytes, drift_receipt = atlas.build_from_spec(root, spec)
        finally:
            atlas.PIL.__version__ = original_version
        if drift_receipt == first_receipt:
            raise AssertionError("Pillow runtime version drift was not reflected in the receipt")
        if drift_bytes != first_bytes:
            raise AssertionError("test-only runtime label drift unexpectedly changed pixels")

        original_import_error = atlas.PILLOW_IMPORT_ERROR
        original_pil = atlas.PIL
        try:
            atlas.PILLOW_IMPORT_ERROR = ImportError("simulated missing dependency")
            atlas.PIL = None
            expect_error("missing Pillow", lambda: atlas.build_from_spec(root, spec), "Pillow is required")
        finally:
            atlas.PILLOW_IMPORT_ERROR = original_import_error
            atlas.PIL = original_pil

    print(
        "PASS: atlas v2 accepts PNG/JPEG/WebP, preserves native pixels without scaling, "
        "pads mixed sizes deterministically, emits RGB8 PNG, locks decoder/encoder versions, "
        "and fails closed on tamper, low resolution, animation, unsupported codecs, one-panel groups, or missing Pillow"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
