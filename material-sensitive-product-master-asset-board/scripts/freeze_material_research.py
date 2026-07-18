#!/usr/bin/env python3
"""Freeze one auditable material-product research artifact, create-only."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from material_research import (
    ResearchContractError,
    canonical_json_bytes,
    freeze_research_document,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--draft", required=True, type=Path, help="material_research_draft.v1 JSON")
    parser.add_argument(
        "--run-dir",
        required=True,
        type=Path,
        help="existing immutable run; output is exactly sources/material-research.json",
    )
    return parser.parse_args()


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def freeze_to_run(draft_path_arg: Path, run_dir_arg: Path) -> tuple[str, Path, dict[str, object]]:
    draft_path = draft_path_arg.resolve(strict=True)
    if not draft_path.is_file():
        raise ResearchContractError("blocked_material_research_invalid", f"draft is not a file: {draft_path}")
    run_dir = run_dir_arg.resolve(strict=True)
    if not run_dir.is_dir():
        raise ResearchContractError("blocked_material_research_invalid", f"run-dir is not a directory: {run_dir}")
    capture_root = (run_dir / "sources" / "research-captures").resolve(strict=True)
    if not capture_root.is_dir():
        raise ResearchContractError(
            "blocked_research_materialization",
            f"run-scoped capture directory is required: {capture_root}",
        )
    draft = json.loads(draft_path.read_text(encoding="utf-8"))
    frozen = freeze_research_document(draft, draft_dir=draft_path.parent)
    for item in frozen["evidence"]:
        capture = item["capture"]
        if capture is None:
            continue
        capture_path = Path(capture["local_path"]).resolve(strict=True)
        if not _is_within(capture_path, capture_root):
            raise ResearchContractError(
                "blocked_research_capture_not_run_scoped",
                f"capture must already be retained under {capture_root}: {capture_path}",
            )
    output = run_dir / "sources" / "material-research.json"
    payload = canonical_json_bytes(frozen)
    if output.exists():
        if not output.is_file() or output.read_bytes() != payload:
            raise ResearchContractError(
                "blocked_material_research_output_conflict",
                f"existing frozen output differs: {output}",
            )
        return "already_frozen", output, frozen
    with output.open("xb") as handle:
        handle.write(payload)
    return "frozen", output, frozen


def main() -> int:
    args = parse_args()
    try:
        status, output, frozen = freeze_to_run(args.draft, args.run_dir)
    except (OSError, UnicodeError, json.JSONDecodeError, ResearchContractError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(
        json.dumps(
            {
                "status": status,
                "schema": frozen["schema"],
                "output": str(output),
                "artifact_sha256": frozen["artifact_sha256"],
                "evidence_count": len(frozen["evidence"]),
                "selected_generation_reference_count": sum(
                    1 for item in frozen["evidence"] if item["selected_generation_reference"]
                ),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
