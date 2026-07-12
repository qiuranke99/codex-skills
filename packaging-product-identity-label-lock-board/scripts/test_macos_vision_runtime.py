#!/usr/bin/env python3
"""Live macOS Vision smoke for fictional text, EAN-13, and QR final pixels."""

from __future__ import annotations

import argparse
import json
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import run_post_composite_verification as post_adapter


EAN_PAYLOAD = "2901234567896"
QR_PAYLOAD = "https://product.example.invalid/example-lab-7q4/test-oil"
TEXT_LINES = ("EXAMPLE LAB 7Q4", "TEST BOTANICAL OIL")

L_PATTERNS = (
    "0001101", "0011001", "0010011", "0111101", "0100011",
    "0110001", "0101111", "0111011", "0110111", "0001011",
)
G_PATTERNS = (
    "0100111", "0110011", "0011011", "0100001", "0011101",
    "0111001", "0000101", "0010001", "0001001", "0010111",
)
R_PATTERNS = tuple("".join("1" if bit == "0" else "0" for bit in value) for value in L_PATTERNS)
PARITY = ("LLLLLL", "LLGLGG", "LLGGLG", "LLGGGL", "LGLLGG", "LGGLLG", "LGGGLL", "LGLGLG", "LGLGGL", "LGGLGL")


class SmokeError(RuntimeError):
    pass


def validate_ean(payload: str) -> None:
    passed, method = post_adapter.decoded_payload_integrity("EAN-13", payload)
    if not passed or method != "ean13_mod10":
        raise SmokeError("fictional EAN-13 fixture checksum is invalid")


def render_ean13(payload: str, module: int = 8, bar_height: int = 340) -> Image.Image:
    validate_ean(payload)
    digits = [int(value) for value in payload]
    left = "".join(
        (L_PATTERNS if family == "L" else G_PATTERNS)[digit]
        for family, digit in zip(PARITY[digits[0]], digits[1:7])
    )
    right = "".join(R_PATTERNS[digit] for digit in digits[7:])
    bits = "101" + left + "01010" + right + "101"
    quiet = 12
    image = Image.new("RGB", ((len(bits) + quiet * 2) * module, bar_height + 70), "white")
    draw = ImageDraw.Draw(image)
    for index, bit in enumerate(bits):
        if bit == "1":
            x0 = (quiet + index) * module
            guard = index < 3 or 45 <= index < 50 or index >= 92
            draw.rectangle((x0, 10, x0 + module - 1, bar_height + (25 if guard else 0)), fill="black")
    font = ImageFont.load_default(size=30)
    draw.text((quiet * module, bar_height + 30), payload, fill="black", font=font)
    return image


def font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for locator in (
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ):
        try:
            return ImageFont.truetype(locator, size=size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


def generate_qr(output: Path) -> None:
    swift = shutil.which("swift")
    if not swift:
        raise SmokeError("Swift is unavailable")
    source = output.with_suffix(".swift")
    source.write_text(
        """import AppKit
import CoreImage
import Foundation

let args = CommandLine.arguments
guard args.count == 3 else { exit(2) }
guard let filter = CIFilter(name: "CIQRCodeGenerator") else { exit(3) }
filter.setValue(Data(args[1].utf8), forKey: "inputMessage")
filter.setValue("M", forKey: "inputCorrectionLevel")
guard let raw = filter.outputImage else { exit(4) }
let scaled = raw.transformed(by: CGAffineTransform(scaleX: 18, y: 18))
let context = CIContext(options: nil)
guard let cg = context.createCGImage(scaled, from: scaled.extent) else { exit(5) }
let rep = NSBitmapImageRep(cgImage: cg)
guard let data = rep.representation(using: .png, properties: [:]) else { exit(6) }
try data.write(to: URL(fileURLWithPath: args[2]))
""",
        encoding="utf-8",
    )
    result = subprocess.run(
        [swift, str(source), QR_PAYLOAD, str(output)],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 or not output.is_file():
        raise SmokeError(f"fictional QR generation failed ({result.returncode}): {result.stderr.strip()}")


def build_fixture(root: Path) -> Path:
    canvas = Image.new("RGB", (2400, 1200), "white")
    draw = ImageDraw.Draw(canvas)
    draw.text((100, 70), TEXT_LINES[0], fill="black", font=font(132))
    draw.text((100, 235), TEXT_LINES[1], fill="black", font=font(108))
    canvas.paste(render_ean13(EAN_PAYLOAD), (100, 535))
    qr_path = root / "fictional_qr.png"
    generate_qr(qr_path)
    with Image.open(qr_path) as qr:
        qr_rgb = qr.convert("RGB")
        canvas.paste(qr_rgb, (1650, 520))
    fixture = root / "fictional_final_master.png"
    canvas.save(fixture, format="PNG", optimize=False)
    return fixture


def run(require_live: bool) -> dict[str, object]:
    if platform.system() != "Darwin":
        if require_live:
            raise SmokeError("live macOS Vision runtime is required but this host is not Darwin")
        return {"status": "SKIP_NON_DARWIN", "engine": "bundled_macos_vision_ocr"}
    with tempfile.TemporaryDirectory(prefix="packaging-vision-smoke-") as temp:
        fixture = build_fixture(Path(temp))
        values, engine_version = post_adapter.run_bundled_vision([fixture], ["en-US"])
    if len(values) != 1:
        raise SmokeError("Vision returned the wrong fixture count")
    observed_text = "\n".join(
        str(item.get("text", "")) for item in values[0].get("text_observations", [])
        if isinstance(item, dict)
    ).upper()
    if "EXAMPLE" not in observed_text or "7Q4" not in observed_text or "BOTANICAL" not in observed_text:
        raise SmokeError(f"Vision did not recover the fictional label text: {observed_text!r}")
    codes = {
        (post_adapter.canonical_symbology(str(item.get("symbology", ""))), str(item.get("payload", "")))
        for item in values[0].get("code_observations", []) if isinstance(item, dict)
    }
    if ("EAN-13", EAN_PAYLOAD) not in codes:
        raise SmokeError(f"Vision did not decode the fictional EAN-13: {sorted(codes)}")
    if ("QR", QR_PAYLOAD) not in codes:
        raise SmokeError(f"Vision did not decode the fictional QR: {sorted(codes)}")
    return {
        "status": "PASS",
        "engine": "bundled_macos_vision_ocr",
        "engine_version": engine_version,
        "text_markers": ["EXAMPLE", "7Q4", "BOTANICAL"],
        "codes": [["EAN-13", EAN_PAYLOAD], ["QR", QR_PAYLOAD]],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-live", action="store_true")
    args = parser.parse_args()
    try:
        result = run(args.require_live)
    except Exception as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False, sort_keys=True))
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
