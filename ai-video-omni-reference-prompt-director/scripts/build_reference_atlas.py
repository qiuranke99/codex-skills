#!/usr/bin/env python3
"""Build a byte-reproducible, non-generative RGB8 PNG reference atlas.

The compositor accepts the common still-image transports used by the fixed
asset owners (PNG, JPEG, and WebP), decodes them with a frozen Pillow policy,
never resizes a panel, and emits a metadata-free RGB8 PNG with fixed encoder
parameters.  The receipt records the exact Pillow and codec backend versions;
the package validator rebuilds both bytes and receipt, so runtime drift fails
closed instead of silently changing pixels.
"""

from __future__ import annotations

import hashlib
import io
import json
import math
import sys
import warnings
from pathlib import Path
from typing import Any

try:
    import PIL
    from PIL import Image, ImageCms, ImageOps, features
except ImportError as exc:  # pragma: no cover - exercised by explicit fail-closed test
    PIL = None  # type: ignore[assignment]
    Image = None  # type: ignore[assignment]
    ImageCms = None  # type: ignore[assignment]
    ImageOps = None  # type: ignore[assignment]
    features = None  # type: ignore[assignment]
    PILLOW_IMPORT_ERROR: ImportError | None = exc
else:
    PILLOW_IMPORT_ERROR = None


MINIMUM_ATLAS_PANEL_WIDTH_PIXELS = 256
MINIMUM_ATLAS_PANEL_HEIGHT_PIXELS = 256
ATLAS_LEGIBILITY_POLICY = "identity_geometry_look_only_no_microcopy"
ATLAS_SPEC_VERSION = "ai-video-deterministic-atlas-spec.v2"
ATLAS_RECEIPT_VERSION = "ai-video-deterministic-atlas-receipt.v2"
ATLAS_CODEC = "PNG_RGB8"
ATLAS_MEDIA_TYPE = "image/png"
SOURCE_DECODE_POLICY = "pillow_common_raster_to_rgb8_no_resize_v1"
OUTPUT_ENCODE_POLICY = "pillow_png_rgb8_fixed_v1"
ATLAS_LAYOUT_POLICY = "max_native_cell_center_floor_no_resize_v1"
SUPPORTED_SOURCE_FORMATS = {"PNG", "JPEG", "WEBP"}
PNG_ENCODER_PARAMETERS: dict[str, Any] = {
    "compress_level": 9,
    "optimize": False,
    "interlace": 0,
    "metadata": "none",
}
ALLOWED_ATLAS_CONTROL_ROLES = {
    "identity", "wardrobe", "product_geometry", "material_behavior", "scene_canon",
    "global_look", "storyboard", "keyframe_state", "keyframe_boundary",
}
ATLAS_CONTROL_ROLE_ORDER = (
    "identity", "wardrobe", "product_geometry", "material_behavior", "scene_canon",
    "global_look", "storyboard", "keyframe_state", "keyframe_boundary",
)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _require_pillow() -> None:
    if PILLOW_IMPORT_ERROR is not None or PIL is None or Image is None:
        detail = f": {PILLOW_IMPORT_ERROR}" if PILLOW_IMPORT_ERROR else ""
        raise ValueError(
            "Pillow is required for deterministic PNG/JPEG/WebP atlas decoding and PNG encoding"
            + detail
        )


def _feature_version(kind: str, name: str) -> str:
    _require_pillow()
    assert features is not None
    try:
        value = features.version_codec(name) if kind == "codec" else features.version_module(name)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"required Pillow backend is unavailable: {name}") from exc
    if not isinstance(value, str) or not value:
        raise ValueError(f"required Pillow backend is unavailable: {name}")
    return value


def _decoder_backend(source_format: str) -> dict[str, str]:
    if source_format == "PNG":
        return {"backend": "zlib", "backend_version": _feature_version("codec", "zlib")}
    if source_format == "JPEG":
        return {"backend": "libjpeg", "backend_version": _feature_version("codec", "jpg")}
    if source_format == "WEBP":
        return {"backend": "libwebp", "backend_version": _feature_version("module", "webp")}
    raise ValueError(f"unsupported source codec: {source_format}")


def _runtime_receipts(source_formats: set[str], used_icc_transform: bool) -> tuple[dict[str, Any], dict[str, Any]]:
    _require_pillow()
    assert PIL is not None
    codec_backends = [
        {"source_codec": source_format, **_decoder_backend(source_format)}
        for source_format in sorted(source_formats)
    ]
    decoder: dict[str, Any] = {
        "implementation": "Pillow",
        "implementation_version": PIL.__version__,
        "policy": SOURCE_DECODE_POLICY,
        "codec_backends": codec_backends,
        "exif_orientation_policy": "lossless_transpose_before_dimension_check",
        "alpha_policy": "composite_over_spec_background_rgb",
        "color_profile_policy": "embedded_icc_to_srgb_else_raw_samples_as_srgb",
    }
    if used_icc_transform:
        decoder["color_management_backend"] = {
            "backend": "LittleCMS",
            "backend_version": _feature_version("module", "littlecms2"),
        }
    else:
        decoder["color_management_backend"] = None
    encoder = {
        "implementation": "Pillow",
        "implementation_version": PIL.__version__,
        "policy": OUTPUT_ENCODE_POLICY,
        "backend": "zlib",
        "backend_version": _feature_version("codec", "zlib"),
        "parameters": dict(PNG_ENCODER_PARAMETERS),
    }
    return decoder, encoder


def _embedded_icc_to_srgb(image: Any, icc_profile: bytes) -> Any:
    _require_pillow()
    assert ImageCms is not None
    try:
        source_profile = ImageCms.ImageCmsProfile(io.BytesIO(icc_profile))
        destination_profile = ImageCms.createProfile("sRGB")
        return ImageCms.profileToProfile(
            image,
            source_profile,
            destination_profile,
            renderingIntent=0,
            outputMode="RGB",
            inPlace=False,
            flags=0,
        )
    except Exception as exc:
        raise ValueError("embedded ICC profile could not be deterministically converted to sRGB") from exc


def decode_common_raster(path: Path, background_rgb: tuple[int, int, int]) -> dict[str, Any]:
    """Decode one source to RGB8 without scaling and return evidence."""

    _require_pillow()
    assert Image is not None and ImageOps is not None
    data = path.read_bytes()
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as opened:
                source_format = str(opened.format or "").upper()
                if source_format not in SUPPORTED_SOURCE_FORMATS:
                    raise ValueError(
                        f"{path}: unsupported source codec {source_format or 'unknown'}; "
                        "expected PNG, JPEG, or WebP"
                    )
                if int(getattr(opened, "n_frames", 1)) != 1 or bool(getattr(opened, "is_animated", False)):
                    raise ValueError(f"{path}: animated or multi-frame sources are forbidden")
                source_mode = str(opened.mode)
                source_width, source_height = opened.size
                try:
                    exif_orientation = int(opened.getexif().get(274, 1))
                except (AttributeError, TypeError, ValueError):
                    exif_orientation = 1
                if exif_orientation not in range(1, 9):
                    raise ValueError(f"{path}: invalid EXIF orientation")
                icc_profile = opened.info.get("icc_profile")
                if icc_profile is not None and not isinstance(icc_profile, bytes):
                    raise ValueError(f"{path}: malformed embedded ICC profile")
                opened.load()
                oriented = ImageOps.exif_transpose(opened)
                has_alpha = "A" in oriented.getbands() or "transparency" in opened.info
                alpha = oriented.convert("RGBA").getchannel("A") if has_alpha else None
                color_source = oriented.convert("RGB", dither=Image.Dither.NONE)
                if icc_profile:
                    rgb = _embedded_icc_to_srgb(color_source, icc_profile)
                else:
                    rgb = color_source
                if alpha is not None:
                    rgba = rgb.convert("RGBA")
                    rgba.putalpha(alpha)
                    canvas = Image.new("RGBA", rgb.size, (*background_rgb, 255))
                    rgb = Image.alpha_composite(canvas, rgba).convert("RGB")
                width, height = rgb.size
                pixels = rgb.tobytes("raw", "RGB")
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(f"{path}: Pillow could not decode the source deterministically") from exc
    if len(pixels) != width * height * 3:
        raise ValueError(f"{path}: decoded RGB8 byte count mismatch")
    backend = _decoder_backend(source_format)
    return {
        "source_codec": source_format,
        "source_mode": source_mode,
        "source_width": source_width,
        "source_height": source_height,
        "exif_orientation": exif_orientation,
        "normalized_width": width,
        "normalized_height": height,
        "icc_profile_sha256": sha256_bytes(icc_profile) if icc_profile else None,
        "alpha_composited": alpha is not None,
        "decoded_rgb_sha256": sha256_bytes(pixels),
        "decoder_backend": backend,
        "pixels": pixels,
    }


def encode_png(width: int, height: int, pixels: bytes) -> bytes:
    _require_pillow()
    assert Image is not None
    if len(pixels) != width * height * 3:
        raise ValueError("atlas pixel byte count mismatch")
    image = Image.frombytes("RGB", (width, height), pixels, "raw", "RGB")
    output = io.BytesIO()
    image.save(
        output,
        format="PNG",
        compress_level=PNG_ENCODER_PARAMETERS["compress_level"],
        optimize=PNG_ENCODER_PARAMETERS["optimize"],
        interlace=PNG_ENCODER_PARAMETERS["interlace"],
    )
    value = output.getvalue()
    if not value.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("Pillow did not emit a PNG atlas")
    return value


def compose(
    sources: list[dict[str, Any]],
    columns: int,
    background_rgb: tuple[int, int, int],
) -> tuple[bytes, list[dict[str, Any]], int, int]:
    if len(sources) < 2:
        raise ValueError("atlas requires at least two sources")
    if columns <= 0:
        raise ValueError("columns must be positive")
    cell_width = max(source["normalized_width"] for source in sources)
    cell_height = max(source["normalized_height"] for source in sources)
    columns = min(columns, len(sources))
    rows = math.ceil(len(sources) / columns)
    width, height = columns * cell_width, rows * cell_height
    background = bytes(background_rgb)
    pixels = bytearray(background * (width * height))
    panels: list[dict[str, Any]] = []
    for index, source in enumerate(sources):
        cell_x = (index % columns) * cell_width
        cell_y = (index // columns) * cell_height
        panel_width = source["normalized_width"]
        panel_height = source["normalized_height"]
        x = cell_x + (cell_width - panel_width) // 2
        y = cell_y + (cell_height - panel_height) // 2
        src_pixels = source["pixels"]
        for row in range(panel_height):
            src_start = row * panel_width * 3
            dst_start = ((y + row) * width + x) * 3
            pixels[dst_start:dst_start + panel_width * 3] = src_pixels[src_start:src_start + panel_width * 3]
        panels.append({key: value for key, value in source.items() if key != "pixels"} | {
            "x": x,
            "y": y,
            "width": panel_width,
            "height": panel_height,
            "cell_x": cell_x,
            "cell_y": cell_y,
            "cell_width": cell_width,
            "cell_height": cell_height,
        })
    return encode_png(width, height, bytes(pixels)), panels, width, height


def resolve_project_path(root: Path, value: str, portable_locator: bool = False) -> Path:
    if portable_locator and (
        "\\" in value
        or value.startswith("/")
        or (len(value) > 1 and value[0].isalpha() and value[1] == ":")
    ):
        raise ValueError(f"serialized atlas source must use portable POSIX project-relative syntax: {value}")
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = root / candidate
    resolved = candidate.resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(f"path escapes package root: {value}") from exc
    return resolved


def build_from_spec(root: Path, spec: dict[str, Any]) -> tuple[bytes, dict[str, Any]]:
    required = {
        "schema_version", "atlas_id", "generation_unit_id", "layout_columns", "background_rgb",
        "minimum_panel_width_pixels", "minimum_panel_height_pixels", "legibility_policy",
        "source_decode_policy", "output_encode_policy", "layout_policy", "output_codec", "sources",
    }
    if set(spec) != required or spec.get("schema_version") != ATLAS_SPEC_VERSION:
        raise ValueError("atlas spec exact v2 fields/schema required")
    if spec.get("source_decode_policy") != SOURCE_DECODE_POLICY:
        raise ValueError("atlas source_decode_policy differs from the frozen builder")
    if spec.get("output_encode_policy") != OUTPUT_ENCODE_POLICY or spec.get("output_codec") != ATLAS_CODEC:
        raise ValueError("atlas output codec/policy differs from the frozen RGB8 PNG builder")
    if spec.get("layout_policy") != ATLAS_LAYOUT_POLICY:
        raise ValueError("atlas layout_policy differs from the frozen no-resize cell compositor")
    background = spec.get("background_rgb")
    if not isinstance(background, list) or len(background) != 3 or any(
        not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 255
        for value in background
    ):
        raise ValueError("background_rgb must contain three RGB8 integers")
    raw_sources = spec.get("sources")
    if not isinstance(raw_sources, list):
        raise ValueError("sources must be an array")
    minimum_width = spec.get("minimum_panel_width_pixels")
    minimum_height = spec.get("minimum_panel_height_pixels")
    if not isinstance(minimum_width, int) or isinstance(minimum_width, bool) or minimum_width < MINIMUM_ATLAS_PANEL_WIDTH_PIXELS:
        raise ValueError(f"minimum_panel_width_pixels must be at least {MINIMUM_ATLAS_PANEL_WIDTH_PIXELS}")
    if not isinstance(minimum_height, int) or isinstance(minimum_height, bool) or minimum_height < MINIMUM_ATLAS_PANEL_HEIGHT_PIXELS:
        raise ValueError(f"minimum_panel_height_pixels must be at least {MINIMUM_ATLAS_PANEL_HEIGHT_PIXELS}")
    if spec.get("legibility_policy") != ATLAS_LEGIBILITY_POLICY:
        raise ValueError("atlas legibility_policy must forbid microcopy transport")
    source_records: list[dict[str, Any]] = []
    seen: set[str] = set()
    source_formats: set[str] = set()
    used_icc_transform = False
    for index, item in enumerate(raw_sources):
        if not isinstance(item, dict) or set(item) != {
            "artifact_id", "file_path", "file_sha256", "control_roles", "control_role"
        }:
            raise ValueError(f"sources[{index}] exact fields required")
        artifact_id = item.get("artifact_id")
        if not isinstance(artifact_id, str) or not artifact_id or artifact_id in seen:
            raise ValueError(f"sources[{index}] artifact_id must be unique")
        seen.add(artifact_id)
        control_roles = item.get("control_roles")
        control_role = item.get("control_role")
        if (
            not isinstance(control_roles, list) or not control_roles
            or any(not isinstance(role, str) or not role for role in control_roles)
            or len(control_roles) != len(set(control_roles))
            or control_role not in control_roles
        ):
            raise ValueError(f"sources[{index}] requires canonical unique control_roles and one primary control_role")
        if "label_copy" in control_roles:
            raise ValueError(f"sources[{index}] label_copy cannot be transported through an atlas")
        if not set(control_roles) <= ALLOWED_ATLAS_CONTROL_ROLES:
            raise ValueError(f"sources[{index}] control_roles cannot be transported through an atlas")
        if control_roles != sorted(control_roles, key=ATLAS_CONTROL_ROLE_ORDER.index):
            raise ValueError(f"sources[{index}] control_roles must follow canonical semantic order")
        path = resolve_project_path(root, str(item.get("file_path", "")), portable_locator=True)
        source_bytes = path.read_bytes()
        actual_hash = sha256_bytes(source_bytes)
        if item.get("file_sha256") != actual_hash:
            raise ValueError(f"sources[{index}] file hash mismatch")
        decoded = decode_common_raster(path, tuple(background))
        width = decoded["normalized_width"]
        height = decoded["normalized_height"]
        if width < minimum_width or height < minimum_height:
            raise ValueError(f"sources[{index}] panel dimensions are below the frozen legibility threshold")
        source_formats.add(decoded["source_codec"])
        used_icc_transform = used_icc_transform or decoded["icc_profile_sha256"] is not None
        source_records.append({
            "artifact_id": artifact_id,
            "file_path": item["file_path"],
            "file_sha256": actual_hash,
            "control_roles": control_roles,
            "control_role": control_role,
            **decoded,
        })
    atlas_bytes, panels, width, height = compose(
        source_records,
        int(spec.get("layout_columns", 0)),
        tuple(background),
    )
    decoder_runtime, encoder_runtime = _runtime_receipts(source_formats, used_icc_transform)
    receipt = {
        "schema_version": ATLAS_RECEIPT_VERSION,
        "atlas_id": spec["atlas_id"],
        "generation_unit_id": spec["generation_unit_id"],
        "codec": ATLAS_CODEC,
        "media_type": ATLAS_MEDIA_TYPE,
        "width": width,
        "height": height,
        "layout_columns": min(int(spec["layout_columns"]), len(source_records)),
        "background_rgb": background,
        "minimum_panel_width_pixels": minimum_width,
        "minimum_panel_height_pixels": minimum_height,
        "legibility_policy": ATLAS_LEGIBILITY_POLICY,
        "layout_policy": ATLAS_LAYOUT_POLICY,
        "decoder_runtime": decoder_runtime,
        "encoder_runtime": encoder_runtime,
        "panels": panels,
        "atlas_file_sha256": sha256_bytes(atlas_bytes),
    }
    return atlas_bytes, receipt


def main(argv: list[str]) -> int:
    if len(argv) != 5:
        print("usage: build_reference_atlas.py <package_root> <spec.json> <atlas.png> <receipt.json>", file=sys.stderr)
        return 2
    root = Path(argv[1]).resolve()
    spec_path = resolve_project_path(root, argv[2])
    atlas_path = resolve_project_path(root, argv[3])
    receipt_path = resolve_project_path(root, argv[4])
    if atlas_path.suffix.lower() != ".png":
        print("ERROR: deterministic atlas output path must end in .png", file=sys.stderr)
        return 1
    try:
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
        atlas_bytes, receipt = build_from_spec(root, spec)
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    atlas_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    atlas_path.write_bytes(atlas_bytes)
    receipt_path.write_bytes((json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8"))
    print(f"PASS: wrote deterministic RGB8 PNG atlas {atlas_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
