#!/usr/bin/env python3
"""Probe a control-video file into deterministic, validator-comparable evidence."""

from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
import sys
from fractions import Fraction
from pathlib import Path
from typing import Any


PROBE_CONTRACT_VERSION = "ffprobe-media-evidence.v1"


class MediaProbeError(RuntimeError):
    """The media or the required probe tool cannot satisfy the evidence contract."""


def _finite_float(value: Any, label: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise MediaProbeError(f"{label} is not numeric") from exc
    if not math.isfinite(result):
        raise MediaProbeError(f"{label} is not finite")
    return result


def _canonical_rate(value: Any) -> str:
    if not isinstance(value, str) or value in {"", "0/0", "N/A"}:
        raise MediaProbeError("video frame rate is unavailable")
    try:
        rate = Fraction(value)
    except (ValueError, ZeroDivisionError) as exc:
        raise MediaProbeError("video frame rate is invalid") from exc
    if rate <= 0:
        raise MediaProbeError("video frame rate must be positive")
    return f"{rate.numerator}/{rate.denominator}"


def resolve_ffprobe(binary: str) -> str:
    if not isinstance(binary, str) or not binary:
        raise MediaProbeError("ffprobe executable is not configured")
    if "/" in binary:
        path = Path(binary).expanduser().resolve()
        if not path.is_file():
            raise MediaProbeError(f"ffprobe executable not found: {binary}")
        return str(path)
    resolved = shutil.which(binary)
    if resolved is None:
        raise MediaProbeError(f"ffprobe executable not found: {binary}")
    return resolved


def probe_media(path: Path, ffprobe_binary: str = "ffprobe") -> dict[str, Any]:
    """Decode-count one video and return only stable semantic probe fields."""

    media_path = path.resolve()
    if not media_path.is_file():
        raise MediaProbeError(f"media file not found: {media_path}")
    ffprobe = resolve_ffprobe(ffprobe_binary)
    command = [
        ffprobe,
        "-v", "error",
        "-count_frames",
        "-count_packets",
        "-show_format",
        "-show_streams",
        "-show_chapters",
        "-print_format", "json",
        str(media_path),
    ]
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        detail = getattr(exc, "stderr", None)
        suffix = f": {str(detail).strip()}" if detail else ""
        raise MediaProbeError(f"ffprobe could not decode-count the media{suffix}") from exc
    try:
        raw = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise MediaProbeError("ffprobe returned invalid JSON") from exc
    streams = raw.get("streams")
    if not isinstance(streams, list):
        raise MediaProbeError("ffprobe returned no stream list")
    video_streams = [item for item in streams if isinstance(item, dict) and item.get("codec_type") == "video"]
    audio_streams = [item for item in streams if isinstance(item, dict) and item.get("codec_type") == "audio"]
    if len(video_streams) != 1:
        raise MediaProbeError("control media must contain exactly one video stream")
    video = video_streams[0]
    width = video.get("width")
    height = video.get("height")
    if not isinstance(width, int) or isinstance(width, bool) or width < 2:
        raise MediaProbeError("video width is invalid")
    if not isinstance(height, int) or isinstance(height, bool) or height < 2:
        raise MediaProbeError("video height is invalid")
    frame_rate = _canonical_rate(video.get("avg_frame_rate") or video.get("r_frame_rate"))
    frame_count_raw = video.get("nb_read_frames")
    try:
        decoded_frame_count = int(frame_count_raw)
    except (TypeError, ValueError) as exc:
        raise MediaProbeError("decoded frame count is unavailable") from exc
    if decoded_frame_count < 1:
        raise MediaProbeError("decoded frame count must be positive")
    packet_count_raw = video.get("nb_read_packets")
    try:
        decoded_packet_count = int(packet_count_raw)
    except (TypeError, ValueError) as exc:
        raise MediaProbeError("decoded packet count is unavailable") from exc
    if decoded_packet_count < 1:
        raise MediaProbeError("decoded packet count must be positive")
    format_record = raw.get("format") if isinstance(raw.get("format"), dict) else {}
    duration_source = format_record.get("duration", video.get("duration"))
    duration = _finite_float(duration_source, "media duration")
    if duration <= 0:
        raise MediaProbeError("media duration must be positive")
    format_name = format_record.get("format_name")
    if not isinstance(format_name, str) or not format_name:
        raise MediaProbeError("container format is unavailable")
    video_codec = video.get("codec_name")
    if not isinstance(video_codec, str) or not video_codec:
        raise MediaProbeError("video codec is unavailable")
    format_tokens = set(format_name.lower().split(","))
    if "mp4" in format_tokens:
        media_type = "video/mp4"
    elif "webm" in format_tokens:
        media_type = "video/webm"
    elif "mov" in format_tokens:
        media_type = "video/quicktime"
    elif "matroska" in format_tokens:
        media_type = "video/x-matroska"
    else:
        raise MediaProbeError("container media type is not in the deterministic mapping")

    chapters: list[dict[str, Any]] = []
    raw_chapters = raw.get("chapters", [])
    if not isinstance(raw_chapters, list):
        raise MediaProbeError("chapter list is malformed")
    for index, chapter in enumerate(raw_chapters):
        if not isinstance(chapter, dict):
            raise MediaProbeError(f"chapter {index} is malformed")
        tags = chapter.get("tags") if isinstance(chapter.get("tags"), dict) else {}
        title = tags.get("title")
        if not isinstance(title, str) or not title:
            raise MediaProbeError(f"chapter {index} has no title")
        start = _finite_float(chapter.get("start_time"), f"chapter {index} start")
        end = _finite_float(chapter.get("end_time"), f"chapter {index} end")
        if start < 0 or end <= start:
            raise MediaProbeError(f"chapter {index} has invalid boundaries")
        chapters.append({
            "shot_uid": title,
            "start_seconds": round(start, 6),
            "end_seconds": round(end, 6),
        })
    chapters.sort(key=lambda item: (item["start_seconds"], item["end_seconds"], item["shot_uid"]))
    return {
        "probe_contract_version": PROBE_CONTRACT_VERSION,
        "container_format": format_name,
        "media_type": media_type,
        "video_codec": video_codec,
        "duration_seconds": round(duration, 6),
        "width_pixels": width,
        "height_pixels": height,
        "frame_rate": frame_rate,
        "decoded_video_frame_count": decoded_frame_count,
        "decoded_video_packet_count": decoded_packet_count,
        "video_stream_count": len(video_streams),
        "audio_stream_count": len(audio_streams),
        "shot_chapters": chapters,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("media_file", type=Path)
    parser.add_argument("--ffprobe", default="ffprobe")
    args = parser.parse_args()
    try:
        evidence = probe_media(args.media_file, args.ffprobe)
    except MediaProbeError as exc:
        print(f"ERROR: {exc}")
        return 1
    print(json.dumps(evidence, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
