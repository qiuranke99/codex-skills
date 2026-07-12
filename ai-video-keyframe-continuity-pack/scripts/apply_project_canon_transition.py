#!/usr/bin/env python3
"""Fixed-owner atomic Project Canon writer for Keyframe Continuity."""
from pathlib import Path
import sys
SHARED = Path(__file__).resolve().parents[2] / "ai-video-shot-script-director" / "scripts"
sys.path.insert(0, str(SHARED))
from build_asset_canon_export import run_fixed_workflow_canon_writer_cli  # noqa: E402
if __name__ == "__main__":
    raise SystemExit(run_fixed_workflow_canon_writer_cli("ai-video-keyframe-continuity-pack", Path(__file__)))
