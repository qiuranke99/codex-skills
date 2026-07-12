#!/usr/bin/env python3
"""Render a silent cut-timing animatic from storyboard frames and a V1 timeline."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from probe_control_media import MediaProbeError, probe_media


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def inside(root: Path, path: Path, label: str) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as exc:
        raise SystemExit(f"{label} escapes project root") from exc
    return resolved


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("storyboard_manifest", type=Path)
    parser.add_argument("previs_manifest", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--fps", type=int, default=24)
    parser.add_argument("--ffmpeg", default="ffmpeg")
    parser.add_argument("--ffprobe", default="ffprobe")
    parser.add_argument("--project-root", type=Path, required=True, help="explicit project root containing sibling source packages and this Previs package")
    args = parser.parse_args()
    if args.width < 2 or args.height < 2 or args.fps < 1:
        raise SystemExit("width, height, and fps must be positive")
    if not shutil.which(args.ffmpeg) or not shutil.which(args.ffprobe):
        raise SystemExit("ffmpeg and ffprobe are required")

    previs_path = args.previs_manifest.resolve()
    project_root = args.project_root.resolve()
    inside(project_root, previs_path, "previs manifest")
    if previs_path.parent.name != "00_manifest":
        raise SystemExit("previs manifest must be under <package_root>/00_manifest")
    package_root = previs_path.parent.parent.resolve()
    inside(project_root, package_root, "package root")
    if package_root == project_root:
        raise SystemExit("package root must be a strict child of project root")
    storyboard_candidate = args.storyboard_manifest if args.storyboard_manifest.is_absolute() else project_root / args.storyboard_manifest
    storyboard_path = inside(project_root, storyboard_candidate, "storyboard manifest")
    storyboard = load(storyboard_path)
    previs = load(previs_path)
    v1 = previs.get("timing_animatic_v1")
    if not isinstance(v1, dict):
        raise SystemExit("previs manifest has no timing_animatic_v1")
    frames = {frame["shot_uid"]: frame for frame in storyboard.get("frames", [])}
    timeline = v1.get("timeline", [])
    if not timeline:
        raise SystemExit("V1 timeline is empty")

    command = [args.ffmpeg, "-y", "-loglevel", "error"]
    input_paths: list[Path] = []
    for entry in timeline:
        uid = entry["shot_uid"]
        frame = frames.get(uid)
        if frame is None:
            raise SystemExit(f"storyboard frame missing for {uid}")
        frame_path = inside(project_root, storyboard_path.parent.parent / frame["file_path"], f"storyboard frame {uid}")
        if not frame_path.is_file() or sha256_file(frame_path) != frame.get("file_sha256"):
            raise SystemExit(f"storyboard file/hash invalid for {uid}")
        duration = float(entry["duration_seconds"])
        if duration <= 0:
            raise SystemExit(f"nonpositive duration for {uid}")
        input_paths.append(frame_path)
        command.extend(["-loop", "1", "-t", f"{duration:.6f}", "-i", str(frame_path)])

    filters: list[str] = []
    labels: list[str] = []
    for index in range(len(input_paths)):
        label = f"v{index}"
        labels.append(f"[{label}]")
        filters.append(
            f"[{index}:v]scale={args.width}:{args.height}:force_original_aspect_ratio=decrease,"
            f"pad={args.width}:{args.height}:(ow-iw)/2:(oh-ih)/2:black,"
            f"fps={args.fps},setsar=1,format=yuv420p[{label}]"
        )
    filters.append("".join(labels) + f"concat=n={len(labels)}:v=1:a=0[outv]")
    output_candidate = args.output if args.output.is_absolute() else package_root / args.output
    output = inside(package_root, output_candidate, "animatic output")
    output.parent.mkdir(parents=True, exist_ok=True)
    metadata_lines = [";FFMETADATA1"]
    for entry in timeline:
        metadata_lines.extend([
            "[CHAPTER]",
            "TIMEBASE=1/1000000",
            f"START={round(float(entry['start_seconds']) * 1000000)}",
            f"END={round(float(entry['end_seconds']) * 1000000)}",
            f"title={entry['shot_uid']}",
        ])
    with tempfile.TemporaryDirectory(prefix="previs-metadata-") as temp_dir:
        metadata_path = Path(temp_dir) / "timeline.ffmetadata"
        metadata_path.write_bytes(("\n".join(metadata_lines) + "\n").encode("utf-8"))
        metadata_index = len(input_paths)
        command.extend(["-f", "ffmetadata", "-i", str(metadata_path)])
        command.extend([
            "-filter_complex", ";".join(filters), "-map", "[outv]",
            "-map_metadata", str(metadata_index), "-an", "-r", str(args.fps),
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
            "-t", f"{float(timeline[-1]['end_seconds']):.6f}", str(output),
        ])
        subprocess.run(command, check=True)
    try:
        media_probe = probe_media(output, args.ffprobe)
    except MediaProbeError as exc:
        raise SystemExit(f"rendered animatic failed ffprobe evidence gate: {exc}") from exc
    result = {
        "file_path": output.relative_to(package_root).as_posix(),
        "file_sha256": sha256_file(output),
        "actual_duration_seconds": media_probe["duration_seconds"],
        "media_probe": media_probe,
        "silent": True,
        "final_edit_asset": False,
        "render_style": "storyboard_cut_animatic",
        "shot_uids": [entry["shot_uid"] for entry in timeline],
    }
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
