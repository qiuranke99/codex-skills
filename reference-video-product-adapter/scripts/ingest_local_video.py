#!/usr/bin/env python3
"""Ingest a local reference video into analysis assets for the skill."""

from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path
from typing import Any


def run(command: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=check,
    )


def require_tool(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise RuntimeError(f"Required tool not found: {name}. Install ffmpeg, which includes {name}.")
    return path


def parse_fps(value: str | None) -> float:
    if not value or value == "0/0":
        return 0.0
    try:
        return float(Fraction(value))
    except (ValueError, ZeroDivisionError):
        return 0.0


def probe_video(video_path: Path, ffprobe: str) -> tuple[dict[str, Any], dict[str, Any] | None, dict[str, Any] | None]:
    result = run(
        [
            ffprobe,
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(video_path),
        ]
    )
    raw = json.loads(result.stdout)
    streams = raw.get("streams", [])
    video_stream = next((stream for stream in streams if stream.get("codec_type") == "video"), None)
    audio_stream = next((stream for stream in streams if stream.get("codec_type") == "audio"), None)
    if not video_stream:
        raise RuntimeError("No video stream found.")
    return raw, video_stream, audio_stream


def extract_frames(ffmpeg: str, video_path: Path, frames_dir: Path, duration: float, frame_count: int) -> list[str]:
    frames_dir.mkdir(parents=True, exist_ok=True)
    if duration <= 0:
        timestamps = [0.0]
    else:
        count = max(1, frame_count)
        timestamps = [min(duration - 0.05, ((index + 0.5) * duration / count)) for index in range(count)]
        timestamps = [max(0.0, timestamp) for timestamp in timestamps]

    output_files: list[str] = []
    for index, timestamp in enumerate(timestamps, start=1):
        frame_path = frames_dir / f"frame_{index:03d}.jpg"
        run(
            [
                ffmpeg,
                "-y",
                "-ss",
                f"{timestamp:.3f}",
                "-i",
                str(video_path),
                "-frames:v",
                "1",
                "-q:v",
                "2",
                str(frame_path),
            ]
        )
        output_files.append(str(frame_path))
    return output_files


def create_contact_sheet(ffmpeg: str, frames: list[str], contact_sheet: Path) -> None:
    if not frames:
        return
    list_file = contact_sheet.parent / "frames_for_contact_sheet.txt"
    list_file.write_text(
        "\n".join(f"file '{Path(frame).resolve().as_posix()}'" for frame in frames) + "\n",
        encoding="utf-8",
    )
    cols = min(4, len(frames))
    rows = max(1, math.ceil(len(frames) / cols))
    run(
        [
            ffmpeg,
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_file),
            "-vf",
            f"scale=320:-1,tile={cols}x{rows}",
            "-frames:v",
            "1",
            str(contact_sheet),
        ]
    )
    list_file.unlink(missing_ok=True)


def extract_audio(ffmpeg: str, video_path: Path, audio_path: Path) -> bool:
    result = run(
        [
            ffmpeg,
            "-y",
            "-i",
            str(video_path),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            str(audio_path),
        ],
        check=False,
    )
    return result.returncode == 0 and audio_path.exists() and audio_path.stat().st_size > 0


def write_report(report_path: Path, metadata: dict[str, Any]) -> None:
    report_path.write_text(
        "\n".join(
            [
                "# Local Video Ingest Report",
                "",
                "## Source",
                "",
                f"- Source video: {metadata['source_video']}",
                f"- Duration: {metadata['duration_sec']}s",
                f"- Resolution: {metadata['width']}x{metadata['height']}",
                f"- FPS: {metadata['fps']}",
                f"- Video codec: {metadata['video_codec']}",
                f"- Audio codec: {metadata['audio_codec']}",
                "",
                "## Generated Assets",
                "",
                "- Metadata: video_metadata.json",
                f"- Frames: {len(metadata['extracted_frames'])}",
                f"- Contact sheet: {metadata['contact_sheet']}",
                f"- Audio: {metadata['audio_path'] or 'not extracted'}",
                "",
                "## Analysis Notes",
                "",
                "- Use extracted frames and contact sheet as reference evidence.",
                "- Do not copy exact compositions from the reference video.",
                "- If audio transcription is needed, transcribe audio.wav with an approved transcription tool.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def ingest(video_path: Path, package_dir: Path, frame_count: int, extract_audio_enabled: bool) -> Path:
    if not video_path.exists() or not video_path.is_file():
        raise RuntimeError(f"Video file not found: {video_path}")

    ffmpeg = require_tool("ffmpeg")
    ffprobe = require_tool("ffprobe")
    raw, video_stream, audio_stream = probe_video(video_path, ffprobe)
    assert video_stream is not None

    format_info = raw.get("format", {})
    duration = float(format_info.get("duration") or video_stream.get("duration") or 0)
    width = int(video_stream.get("width") or 0)
    height = int(video_stream.get("height") or 0)
    fps = parse_fps(video_stream.get("avg_frame_rate") or video_stream.get("r_frame_rate"))
    frame_count_estimate = float(video_stream.get("nb_frames") or 0)
    if not frame_count_estimate and duration and fps:
        frame_count_estimate = duration * fps

    ingest_dir = package_dir / "01-input" / "local-video"
    frames_dir = ingest_dir / "frames"
    ingest_dir.mkdir(parents=True, exist_ok=True)

    frames = extract_frames(ffmpeg, video_path, frames_dir, duration, frame_count)
    contact_sheet = ingest_dir / "contact_sheet.jpg"
    create_contact_sheet(ffmpeg, frames, contact_sheet)

    audio_path = ingest_dir / "audio.wav"
    audio_written = False
    if extract_audio_enabled and audio_stream:
        audio_written = extract_audio(ffmpeg, video_path, audio_path)

    metadata = {
        "source_video": video_path.name,
        "duration_sec": round(duration, 3),
        "width": width,
        "height": height,
        "fps": round(fps, 3),
        "video_codec": str(video_stream.get("codec_name") or "unknown"),
        "audio_codec": str(audio_stream.get("codec_name") if audio_stream else "none"),
        "frame_count_estimate": round(frame_count_estimate, 3),
        "extracted_frames": [str(Path(frame).relative_to(ingest_dir)) for frame in frames],
        "contact_sheet": str(contact_sheet.relative_to(ingest_dir)) if contact_sheet.exists() else "",
        "audio_path": str(audio_path.relative_to(ingest_dir)) if audio_written else "",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "tools": {
            "ffmpeg": ffmpeg,
            "ffprobe": ffprobe,
        },
    }

    metadata_path = ingest_dir / "video_metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_report(ingest_dir / "local_video_ingest_report.md", metadata)
    return ingest_dir


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract metadata, frames, contact sheet, and audio from a local reference video.")
    parser.add_argument("video_path", help="Path to the local reference video")
    parser.add_argument("output_package_dir", help="Output package directory")
    parser.add_argument("--frames", type=int, default=8, help="Number of frames to extract")
    parser.add_argument("--no-audio", action="store_true", help="Skip audio extraction")
    args = parser.parse_args()

    try:
        ingest(Path(args.video_path), Path(args.output_package_dir), max(1, args.frames), not args.no_audio)
    except Exception as exc:
        print(f"Local video ingest failed: {exc}")
        return 1

    print(f"Local video ingest complete: {Path(args.output_package_dir) / '01-input' / 'local-video'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
