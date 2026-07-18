#!/usr/bin/env python3
"""Fixed aggregate Project Canon runner for ai-video-omni-reference-prompt-director."""

from __future__ import annotations

import sys

from build_asset_canon_export import run_aggregate_cli


if __name__ == "__main__":
    raise SystemExit(
        run_aggregate_cli(["workflow", "--profile", "ai-video-omni-reference-prompt-director", *sys.argv[1:]])
    )
