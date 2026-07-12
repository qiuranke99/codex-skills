#!/usr/bin/env python3
"""Fixed-owner atomic Project Canon writer for Shot Contract revisions."""

from pathlib import Path

from build_asset_canon_export import run_fixed_workflow_canon_writer_cli


if __name__ == "__main__":
    raise SystemExit(
        run_fixed_workflow_canon_writer_cli("ai-video-shot-script-director", Path(__file__))
    )
