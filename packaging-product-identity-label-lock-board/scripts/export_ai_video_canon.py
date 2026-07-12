#!/usr/bin/env python3
"""Fixed-owner AI-video Canon exporter for this asset Skill."""

from pathlib import Path
import sys

SHARED = Path(__file__).resolve().parents[2] / "ai-video-shot-script-director" / "scripts"
sys.path.insert(0, str(SHARED))

from build_asset_canon_export import run_fixed_owner_cli  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(run_fixed_owner_cli("packaging_product", Path(__file__)))
