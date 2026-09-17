#!/usr/bin/env python3
"""Local A-roll sampling and unretouched look-frame extraction; stdlib + FFmpeg."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import struct
import subprocess
import sys
from pathlib import Path


class MediaError(ValueError):
    pass


def run(command: list[str]) -> str:
    try:
        result = subprocess.run(command, capture_output=True, timeout=90, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise MediaError(f"Cannot run {command[0]}: {exc}") from exc
    if result.returncode:
        raise MediaError(result.stderr.decode("utf-8", errors="replace")[-4000:])
    return result.stdout.decode("utf-8", errors="replace")


def executable(name: str) -> str:
    found = shutil.which(name)
    if not found:
        raise MediaError(f"Missing {name}; install separately or use an existing equivalent tool.")
    return found


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def hdr_marked(stream: dict) -> bool:
    return stream.get("color_transfer") in {"smpte2084", "arib-std-b67"} or any(
        "dovi" in str(item.get("side_data_type", "")).lower()
        or "dolby vision" in str(item.get("side_data_type", "")).lower()
        for item in stream.get("side_data_list", [])
    )


def read_media(video: Path) -> dict:
    video = video.resolve(strict=True)
    if not video.is_file():
        raise MediaError("Input must be a local media file.")
    raw = json.loads(run([
        executable("ffprobe"), "-v", "error", "-protocol_whitelist", "file,pipe",
        "-show_streams", "-show_format", "-of", "json", str(video),
    ]))
    stream = next((s for s in raw.get("streams", []) if s.get("codec_type") == "video"
                   and not s.get("disposition", {}).get("attached_pic")), None)
    if stream is None:
        raise MediaError("No non-cover video stream found.")
    if hdr_marked(stream):
        raise MediaError("HDR detected. This helper does not tone-map; prepare and verify a color-managed viewing copy.")
    duration = None
    for value in (stream.get("duration"), raw.get("format", {}).get("duration")):
        try:
            candidate = float(value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(candidate) and candidate > 0:
            duration = candidate
            break
    if duration is None:
        raise MediaError("Cannot establish a finite positive video duration.")
    return {
        "source": str(video), "source_sha256": sha256(video), "duration_seconds": duration,
        "video_stream": stream,
        "format": raw.get("format", {}),
        "color_note": "No enhancement or tone mapping; missing source color tags remain unknown.",
        "time_note": "Requested seconds relative to media start, not a verified decoded-frame PTS.",
    }


def validate_time(at: float, duration: float) -> None:
    if not math.isfinite(at) or not 0 <= at < duration:
        raise MediaError(f"Time must be finite and within [0, {duration}).")


def sample_times(duration: float, count: int) -> list[float]:
    if not math.isfinite(duration) or duration <= 0 or not 2 <= count <= 48:
        raise MediaError("Use a positive duration and 2–48 preview samples.")
    # Bin centers avoid the exact EOF; this is a preview sampling rule, not a shot plan.
    return [duration * (index + 0.5) / count for index in range(count)]


def unused(path: Path) -> None:
    if path.exists() or path.is_symlink():
        raise MediaError(f"Output already exists; choose a new path: {path}")


def png_size(path: Path) -> list[int]:
    with path.open("rb") as stream:
        header = stream.read(24)
    if len(header) != 24 or header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
        raise MediaError("Extraction did not produce a valid PNG header.")
    dimensions = list(struct.unpack(">II", header[16:24]))
    if min(dimensions) <= 0:
        raise MediaError("PNG has invalid dimensions.")
    return dimensions


def frame(media: dict, at: float, output: Path, preview: bool = False) -> dict:
    validate_time(at, media["duration_seconds"])
    unused(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    scale = "scale=320:max(1\\,trunc(320/dar)),setsar=1" if preview else "scale=trunc(iw*sar):ih,setsar=1"
    run([
        executable("ffmpeg"), "-hide_banner", "-loglevel", "error", "-nostdin", "-n",
        "-threads", "2", "-protocol_whitelist", "file,pipe", "-ss", f"{at:.9f}",
        "-i", media["source"], "-map", f"0:{media['video_stream']['index']}",
        "-an", "-frames:v", "1", "-vf", scale, "-threads", "1", str(output),
    ])
    if not output.is_file():
        raise MediaError("No frame decoded at the requested time; choose an earlier timestamp.")
    return {"file": output.name, "requested_seconds": at,
            "width_height": png_size(output), "sha256": sha256(output)}


def write_json(path: Path, data: dict) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def inspect_video(video: Path, out: Path, count: int = 12) -> dict:
    if not 2 <= count <= 48:
        raise MediaError("Use 2–48 preview samples.")
    unused(out)
    media = read_media(video)
    out.mkdir(parents=True)
    frames = []
    for index, at in enumerate(sample_times(media["duration_seconds"], count), 1):
        item = frame(media, at, out / f"sample-{index:02d}.png", preview=True)
        frames.append({"sample": index, **item})
    columns = min(4, count)
    rows = math.ceil(count / columns)
    overview = out / "overview.jpg"
    run([
        executable("ffmpeg"), "-hide_banner", "-loglevel", "error", "-nostdin", "-n",
        "-start_number", "1", "-i", str(out / "sample-%02d.png"),
        "-vf", f"tile={columns}x{rows}:nb_frames={count}:padding=4:margin=4:color=black",
        "-frames:v", "1", "-q:v", "2", str(overview),
    ])
    if not overview.is_file() or not overview.stat().st_size:
        raise MediaError("Contact sheet was not produced.")
    result = {"schema_version": 1, "kind": "inspection", **media, "samples": frames,
              "overview": {"file": overview.name, "sha256": sha256(overview),
                           "columns": columns, "order": "left-to-right, top-to-bottom"},
              "review_status": "not_reviewed; samples do not establish motion or audio review"}
    write_json(out / "inspection.json", result)
    return result


def extract_frame(video: Path, at: float, output: Path) -> dict:
    if output.suffix.lower() != ".png":
        raise MediaError("Reference output must have a .png extension.")
    unused(output)
    unused(output.with_suffix(".json"))
    media = read_media(video)
    item = frame(media, at, output)
    result = {"schema_version": 1, "kind": "reference_frame", **media, "frame": item,
              "review_status": "not_reviewed; open and inspect the exported frame"}
    write_json(output.with_suffix(".json"), result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    inspect = commands.add_parser("inspect", help="metadata, uniform samples and contact sheet")
    inspect.add_argument("--video", type=Path, required=True)
    inspect.add_argument("--out", type=Path, required=True)
    inspect.add_argument("--samples", type=int, default=12)
    extract = commands.add_parser("extract", help="export one look-reference PNG and provenance JSON")
    extract.add_argument("--video", type=Path, required=True)
    extract.add_argument("--at", type=float, required=True)
    extract.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "inspect":
            result = inspect_video(args.video, args.out, args.samples)
            destination = args.out / "inspection.json"
        else:
            result = extract_frame(args.video, args.at, args.output)
            destination = args.output.with_suffix(".json")
        print(json.dumps({"status": "created_not_visually_reviewed", "record": str(destination),
                          "duration_seconds": result["duration_seconds"]}, ensure_ascii=False))
        return 0
    except (MediaError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
