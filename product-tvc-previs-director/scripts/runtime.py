#!/usr/bin/env python3
"""Portable local orchestration. It never uploads assets or submits generation."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone

from core import (ContractError, contract_digest, create_fixture, dump_json,
                  load_contract, safe_path, sha256_file)

PACKAGE = Path(__file__).resolve().parent.parent
VERSION = "1.0.0"


def now():
    return datetime.now(timezone.utc).isoformat()


def read_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        raise ContractError(f"Cannot read JSON {path}: {exc}") from exc


def inside(root, path):
    resolved = Path(path).resolve()
    if not resolved.is_relative_to(Path(root).resolve()):
        raise ContractError(f"Path leaves lane: {path}")
    return resolved


def no_overwrite(path):
    if Path(path).exists():
        raise ContractError(f"Output already exists; use a new versioned lane: {path}")


def package_hashes():
    return {p.relative_to(PACKAGE).as_posix(): sha256_file(p)
            for p in sorted(PACKAGE.rglob("*"))
            if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"}


def mcp_request(lane, mode):
    """Generate a reviewable native MCP request; no subprocess is started here."""
    lane = Path(lane).resolve()
    job_path = lane / ("inspect-job.json" if mode == "inspect" else "job.json")
    if mode == "inspect":
        job = read_json(lane / "job.json")
        job["mode"] = "inspect"
        dump_json(job_path, job)
    # Paths are Python literals in code passed to an actual Python executor, not shell text.
    code = "\n".join([
        "import bpy, os, json, subprocess, time",
        "from pathlib import Path",
        f"lane = Path({str(lane)!r})",
        f"mode = {mode!r}",
        "if not bpy.app.background: raise RuntimeError('Background Blender required')",
        "lock = lane / (mode + '-dispatch.json')",
        "fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY)",
        f"job = {str(job_path)!r}",
        "cmd = [bpy.app.binary_path, '--background']",
        "cmd += [str(lane / 'scene.blend')] if mode == 'inspect' else ['--factory-startup']",
        "cmd += ['--threads', '2', '--python-exit-code', '1', '--python', str(lane / 'code' / 'blender_worker.py'), '--', job]",
        "env = dict(os.environ)",
        "env.update(TMP=str(lane / 'tmp'), TEMP=str(lane / 'tmp'), TMPDIR=str(lane / 'tmp'), PYTHONDONTWRITEBYTECODE='1')",
        "logpath = lane / (mode + '-console.log')",
        "try:",
        "    with open(logpath, 'xb') as log:",
        "        proc = subprocess.Popen(cmd, cwd=str(lane), env=env, stdout=log, stderr=subprocess.STDOUT, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))",
        "    result = {'mode':mode, 'pid':proc.pid, 'dispatcher_pid':os.getpid(), 'command':cmd, 'job':job, 'log':str(logpath), 'started_at_unix':time.time(), 'lane_root':str(lane)}",
        "    with os.fdopen(fd, 'w', encoding='utf-8') as f: json.dump(result, f, indent=2)",
        "except Exception:",
        "    os.close(fd)",
        "    raise",
    ])
    request = {"tool": "mcp__blender__execute_blender_code_for_cli", "arguments": {
        "blend_file": "--factory-startup", "code": code}}
    dump_json(lane / f"mcp-{mode}.json", request)
    return request


def check_layout_review(data, path):
    record = read_json(path)
    if record.get("schema") != "product-tvc-layout-review/v1" or record.get("source_contract_sha256") != contract_digest(data):
        raise ContractError("Layout review does not match the current source contract")
    preview = Path(record.get("preview_lane", "")).resolve()
    preview_lane = read_json(preview / "lane.json")
    if preview_lane.get("source_contract_sha256") != contract_digest(data):
        raise ContractError("Layout preview belongs to another source contract")
    report_path = preview / "layout-report.json"
    report = read_json(report_path)
    if record.get("layout_report_sha256") != sha256_file(report_path) or report.get("issues"):
        raise ContractError("Layout report changed or contains issues")
    if report.get("contract_sha256") != preview_lane["contract_sha256"]:
        raise ContractError("Layout report is not bound to the prepared scene")
    for field in ("reviewer", "method"):
        if not isinstance(record.get(field), str) or not record[field].strip():
            raise ContractError(f"Layout review requires authored {field}")
    comparisons = record.get("layouts")
    if not isinstance(comparisons, list) or {x.get("id") for x in comparisons} != {x["id"] for x in data["layouts"]}:
        raise ContractError("Layout review must cover each source layout exactly")
    assets = {a["id"]: a for a in data["assets"]}
    for layout in data["layouts"]:
        item = next(x for x in comparisons if x.get("id") == layout["id"])
        rendered = next((x for x in report["layouts"] if x["id"] == layout["id"]), None)
        if not rendered:
            raise ContractError(f"Missing rendered layout {layout['id']}")
        image = inside(preview, rendered["image_path"])
        if item.get("source_image_sha256") != assets[layout["image_asset"]]["sha256"] or item.get("preview_image_sha256") != sha256_file(image):
            raise ContractError(f"Layout comparison uses stale images: {layout['id']}")
        if item.get("status") != "pass" or not isinstance(item.get("observations"), str) or not item["observations"].strip():
            raise ContractError(f"Layout needs correction or actual observations: {layout['id']}")
    return record


def prepare(contract_path, out, lane_id, mode="build", layout_review=None):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", lane_id):
        raise ContractError("lane ID must be a short safe identifier")
    source = Path(contract_path).resolve()
    data = load_contract(source)
    if mode not in ("build", "layout"):
        raise ContractError("prepare mode must be layout or build")
    if mode == "build" and not data["fixture"] and not layout_review:
        raise ContractError("Render and compare layouts first; production build needs a bound layout review")
    layout_record = check_layout_review(data, layout_review) if layout_review else None
    lane = Path(out).resolve()
    if lane.is_relative_to(PACKAGE):
        raise ContractError("Run outputs must be outside the Skill package")
    no_overwrite(lane)
    lane.mkdir(parents=True)
    for folder in ("inputs", "code", "tmp", "cache"):
        (lane / folder).mkdir()
    adapted = copy.deepcopy(data)
    for asset in adapted["assets"]:
        src = safe_path(source.parent, asset["path"], must_exist=True)
        relative = f"inputs/{asset['path']}"
        dest = safe_path(lane, relative)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest)
        asset["path"] = relative
    scene = lane / "scene.json"
    dump_json(scene, adapted)
    load_contract(scene)
    for script in ("core.py", "blender_worker.py"):
        shutil.copyfile(PACKAGE / "scripts" / script, lane / "code" / script)
    digest = contract_digest(adapted)
    job = {"schema": "product-tvc-job/v1", "mode": mode, "contract_path": str(scene),
           "contract_sha256": digest, "lane_root": str(lane)}
    dump_json(lane / "job.json", job)
    manifest = {"schema": "product-tvc-lane/v1", "version": VERSION, "created_at": now(),
                "lane_id": lane_id, "stage": mode, "source_contract": str(source),
                "source_contract_sha256": contract_digest(data), "contract_sha256": digest,
                "package_files": package_hashes(), "fixture": data["fixture"],
                "resources": {"blend": str(lane / "scene.blend"), "renders": str(lane / "shots"),
                              "cache": str(lane / "cache"), "temporary": str(lane / "tmp"),
                              "log": str(lane / f"{mode}-console.log")}}
    dump_json(lane / "lane.json", manifest)
    if layout_record:
        dump_json(lane / "layout-review-before-build.json", layout_record)
    mcp_request(lane, mode)
    return {"lane": str(lane), "job": str(lane / "job.json"),
            "mcp_request": str(lane / f"mcp-{mode}.json"), "contract_sha256": digest}


def context(lane):
    lane = Path(lane).resolve()
    manifest = read_json(lane / "lane.json")
    data = load_contract(lane / "scene.json")
    digest = contract_digest(data)
    if digest != manifest["contract_sha256"]:
        raise ContractError("Scene contract changed after prepare; create a new lane")
    for name in ("core.py", "blender_worker.py"):
        expected = manifest["package_files"][f"scripts/{name}"]
        if sha256_file(lane / "code" / name) != expected:
            raise ContractError(f"Prepared worker code changed: {name}")
    return lane, data, manifest


def checked_backend(lane):
    lane, data, manifest = context(lane)
    report = read_json(lane / "backend-report.json")
    if report.get("contract_sha256") != manifest["contract_sha256"]:
        raise ContractError("Backend report belongs to a different contract")
    if report.get("issues"):
        raise ContractError(f"Backend reports {len(report['issues'])} issue(s); fix contract and rebuild")
    if [s["id"] for s in report.get("shots", [])] != [s["id"] for s in data["shots"]]:
        raise ContractError("Backend shot order/coverage differs from contract")
    for shot, measured in zip(data["shots"], report["shots"]):
        if measured.get("issues"):
            raise ContractError(f"Backend shot {shot['id']} has issues")
        if measured.get("frames") != shot["end"] - shot["start"]:
            raise ContractError(f"Wrong rendered frame count for {shot['id']}")
        if (measured.get("start"), measured.get("end")) != (shot["start"], shot["end"]):
            raise ContractError(f"Wrong rendered interval for {shot['id']}")
        directory = inside(lane, measured["directory"])
        actual = sorted(directory.glob("*.png"))
        expected = [directory / f"{i:06d}.png" for i in range(1, measured["frames"] + 1)]
        if actual != expected or any(p.stat().st_size == 0 for p in actual):
            raise ContractError(f"Missing, empty or unexpected frames for {shot['id']}")
        for p in actual:
            with p.open("rb") as stream:
                header = stream.read(24)
            if header[:8] != b"\x89PNG\r\n\x1a\n":
                raise ContractError(f"Invalid PNG: {p}")
            dimensions = [int.from_bytes(header[i:i + 4], "big") for i in (16, 20)]
            if dimensions != data["resolution"]:
                raise ContractError(f"Wrong frame size: {p}")
        if len(measured.get("samples", [])) < 2 * measured["frames"] - 1:
            raise ContractError(f"Missing subframe readback for {shot['id']}")
    return lane, data, manifest, report


def run_command(command, logpath):
    try:
        result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8",
                                errors="replace", timeout=180,
                                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ContractError(f"Local media command failed: {exc}") from exc
    Path(logpath).write_text(json.dumps(command, ensure_ascii=False) + "\n" + result.stdout + result.stderr,
                             encoding="utf-8")
    if result.returncode:
        raise ContractError(f"Local media command exited {result.returncode}; see {logpath}")
    return result.stdout


def probe(path, ffprobe, logpath):
    raw = run_command([ffprobe, "-v", "error", "-select_streams", "v:0", "-count_frames",
                       "-show_entries", "stream=width,height,r_frame_rate,nb_read_frames:format=duration",
                       "-of", "json", str(path)], logpath)
    return json.loads(raw)


def artifact_binding(lane):
    lane = Path(lane)
    names = ["scene.json", "scene.blend", "backend-report.json", "reopen.json", "media-report.json"]
    binding = {}
    for name in names:
        path = lane / name
        if path.is_file():
            binding[name] = sha256_file(path)
    for p in sorted((lane / "media").glob("*.mp4")):
        binding[p.relative_to(lane).as_posix()] = sha256_file(p)
    for p in sorted((lane / "layouts").glob("*.png")):
        binding[p.relative_to(lane).as_posix()] = sha256_file(p)
    return binding


def assemble(lane, ffmpeg="ffmpeg", ffprobe="ffprobe"):
    lane, data, manifest, report = checked_backend(lane)
    no_overwrite(lane / "media-report.json")
    for tool in (ffmpeg, ffprobe):
        if not shutil.which(tool):
            raise ContractError(f"Required local executable not found: {tool}")
    media = lane / "media"
    media.mkdir(exist_ok=True)
    frame_hashes = {}
    clips = []
    for shot in report["shots"]:
        clip = media / f"{shot['id']}.mp4"
        no_overwrite(clip)
        directory = inside(lane, shot["directory"])
        for frame in sorted(directory.glob("*.png")):
            frame_hashes[frame.relative_to(lane).as_posix()] = sha256_file(frame)
        run_command([ffmpeg, "-nostdin", "-v", "error", "-n", "-framerate", str(data["fps"]),
                     "-start_number", "1", "-i", str(directory / "%06d.png"),
                     "-frames:v", str(shot["frames"]), "-an", "-c:v", "libx264", "-preset", "fast",
                     "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(clip)],
                    media / f"{shot['id']}-encode.log")
        result = probe(clip, ffprobe, media / f"{shot['id']}-probe.log")
        stream = result["streams"][0]
        if int(stream["nb_read_frames"]) != shot["frames"]:
            raise ContractError(f"Encoded clip frame count mismatch: {shot['id']}")
        clips.append({"id": shot["id"], "path": str(clip), "sha256": sha256_file(clip), "probe": result})
    # Safe IDs determine filenames; concat never includes user-supplied quoting or protocols.
    concat = media / "concat.txt"
    concat.write_text("".join(f"file '{s['id']}.mp4'\n" for s in report["shots"]), encoding="utf-8")
    full = media / "previs.mp4"
    no_overwrite(full)
    run_command([ffmpeg, "-nostdin", "-v", "error", "-n", "-f", "concat", "-safe", "1", "-i", str(concat),
                 "-an", "-c", "copy", "-movflags", "+faststart", str(full)], media / "concat.log")
    full_probe = probe(full, ffprobe, media / "previs-probe.log")
    stream = full_probe["streams"][0]
    if int(stream["nb_read_frames"]) != data["duration_frames"]:
        raise ContractError("Full video frame count mismatch")
    numerator, denominator = map(int, stream["r_frame_rate"].split("/"))
    if numerator / denominator != data["fps"]:
        raise ContractError("Full video frame rate mismatch")
    if [stream["width"], stream["height"]] != data["resolution"]:
        raise ContractError("Full video resolution mismatch")
    if abs(float(full_probe["format"]["duration"]) - data["duration_frames"] / data["fps"]) > 0.03:
        raise ContractError("Full video duration mismatch")
    # Decode every frame, independently from metadata and count checks.
    run_command([ffmpeg, "-nostdin", "-v", "error", "-i", str(full), "-f", "null", "-"], media / "decode.log")
    result = {"schema": "product-tvc-media/v1", "created_at": now(), "fixture": data["fixture"],
              "contract_sha256": manifest["contract_sha256"], "backend_report_sha256": sha256_file(lane / "backend-report.json"),
              "blend_sha256": sha256_file(lane / "scene.blend"), "frame_hashes": frame_hashes,
              "clips": clips, "full": {"path": str(full), "sha256": sha256_file(full), "probe": full_probe},
              "decoded_all_frames": True, "visual_playback_review": "not_recorded",
              "limitations": ["proxy geometry", "workbench lighting", "no fluid simulation", "no generated final video"]}
    dump_json(lane / "media-report.json", result)
    return {"video": str(full), "frames": data["duration_frames"], "seconds": data["duration_frames"] / data["fps"],
            "report": str(lane / "media-report.json")}


def inspect(lane):
    lane, data, manifest, report = checked_backend(lane)
    media = read_json(lane / "media-report.json")
    if media.get("contract_sha256") != manifest["contract_sha256"]:
        raise ContractError("Media belongs to a different contract")
    if sha256_file(lane / "backend-report.json") != media["backend_report_sha256"]:
        raise ContractError("Backend report changed after media assembly")
    if sha256_file(lane / "scene.blend") != media["blend_sha256"]:
        raise ContractError("Saved Blender file changed after media assembly")
    for relative, expected in media["frame_hashes"].items():
        if sha256_file(safe_path(lane, relative, must_exist=True)) != expected:
            raise ContractError(f"Rendered frame changed: {relative}")
    for clip in media["clips"] + [media["full"]]:
        if sha256_file(inside(lane, clip["path"])) != clip["sha256"]:
            raise ContractError(f"Video changed: {clip['path']}")
    reopen = read_json(lane / "reopen.json")
    if reopen.get("contract_sha256") != manifest["contract_sha256"] or reopen.get("issues"):
        raise ContractError("Cold reopen is missing, mismatched or has issues")
    if reopen.get("worker_pid") == report.get("worker_pid"):
        raise ContractError("Cold reopen must use another Blender process")
    return {"technical_artifacts": "verified", "contract_sha256": manifest["contract_sha256"],
            "frames": data["duration_frames"], "binding": artifact_binding(lane),
            "visual_or_user_approval": "separate evidence required"}


def review(lane, review_path):
    checked = inspect(lane)
    lane = Path(lane).resolve()
    record = read_json(review_path)
    if record.get("binding") != checked["binding"]:
        raise ContractError("Review is not bound to the current complete artifact set")
    for field in ("reviewer", "method", "layout_comparison", "motion_observations", "remaining_issues", "narrative_reconciliation"):
        if not isinstance(record.get(field), str) or not record[field].strip():
            raise ContractError(f"Review requires authored {field}")
    if record.get("playback_complete") is not True or record.get("playback_speed") != 1:
        raise ContractError("Review must explicitly document full original-speed playback")
    if record.get("status") not in ("pass", "needs_revision"):
        raise ContractError("Review status must be pass or needs_revision")
    data = load_contract(lane / "scene.json")
    comparisons = record.get("layouts", [])
    if not isinstance(comparisons, list) or {x.get("id") for x in comparisons if isinstance(x, dict)} != {x["id"] for x in data["layouts"]}:
        raise ContractError("Review requires a comparison for every actual layout")
    assets = {a["id"]: a for a in data["assets"]}
    for layout in data["layouts"]:
        item = next(x for x in comparisons if x.get("id") == layout["id"])
        if item.get("image_sha256") != assets[layout["image_asset"]]["sha256"] or not item.get("observations"):
            raise ContractError(f"Layout review missing current image binding/observations: {layout['id']}")
        if not data["fixture"]:
            provenance = item.get("generation", {})
            for field in ("tool", "input_record", "output_record"):
                if not isinstance(provenance.get(field), str) or not provenance[field].strip():
                    raise ContractError(f"Real layout requires actual generation provenance: {layout['id']} / {field}")
    if record.get("independent") is True and not record.get("sealed_first_review"):
        raise ContractError("Independent review requires a separate sealed-first-review record")
    no_overwrite(lane / "visual-review.json")
    dump_json(lane / "visual-review.json", record)
    return {"review": str(lane / "visual-review.json"), "status": record["status"],
            "meaning": "Authored observation recorded; software cannot prove viewing or user approval"}


def n(value):
    return f"{float(value):.3f}".rstrip("0").rstrip(".")


def measured_camera_text(shot, measured, layout):
    """Describe measured intermediate states, so a prose-only intended path cannot stand in for execution."""
    samples = measured["samples"]
    obj = next(o for o in layout["objects"] if o["id"] == shot["framing"]["object"])
    height = obj["dimensions"][2]
    snapshots = [samples[round(i * (len(samples) - 1) / 4)] for i in range(5)]
    phrases = []
    for sample in snapshots:
        subject = sample["objects"][obj["id"]]["location"]
        delta = [(a-b) / height for a, b in zip(sample["camera_position"], subject)]
        side = "右" if delta[0] > 0.1 else "左" if delta[0] < -0.1 else "正"
        front = "后" if delta[1] > 0 else "前"
        h = sample["bbox"][3] - sample["bbox"][1]
        phrases.append(f"{side}{front}方、相对主体中心高{n(delta[2])}H、距离{n(math.sqrt(sum(x*x for x in delta)))}H、主体占画高约{n(h*100)}%")
    compact = [p for i,p in enumerate(phrases) if i == 0 or p != phrases[i-1]]
    return "以主体初始高度为H，镜内等时间观察点的构图依次为（相邻重复状态合并）：" + " → ".join(compact) + "。按既定连续路径通过中间观察点。"


def expand_template(template, values):
    missing = set(re.findall(r"\{\{([a-z_]+)\}\}", template)) - values.keys()
    if missing:
        raise ContractError(f"Template fields lack a compiler value: {sorted(missing)}")
    return re.sub(r"\{\{([a-z_]+)\}\}", lambda m: str(values[m.group(1)]), template)


def render_prompt(data, report):
    """The package template is the single authority for actual heading order."""
    template = (PACKAGE / "assets" / "prompt-template.md").read_text(encoding="utf-8")
    start = template.index("## {{shot_id}}")
    end = template.index("## 最终落版与停留", start)
    shot_template = template[start:end]
    creative = data["creative"]
    fps = data["fps"]
    gcd = math.gcd(*data["resolution"])
    ids = lambda role: "、".join(a["id"] for a in data["assets"] if a["role"] == role) or "本技术fixture未提供真实产品素材"
    global_values = {
        "duration_seconds": n(data["duration_frames"] / fps),
        "aspect_ratio": ":".join(str(v // gcd) for v in data["resolution"]),
        "visual_intent": creative["concept"], "shot_count": len(data["shots"]),
        "edit_structure": f"{len(data['shots'])-1}次明确切换。", "product_reference_ids": ids("product"),
        "product_identity_scope": "可见身份、结构、比例、材质、状态及可确认文字",
        "look_reference_ids": ids("look"), "look_authority": "色系、整体亮度、明暗比例和光质",
        "previs_reference_ids": "、".join("PREVIS-"+s["id"] for s in data["shots"]),
        "previs_authority": "已读回的代理相机、主体/置景运动和镜头时序",
        "optional_reference_roles": "; ".join(f"{a['id']}：{a['role']}职责" for a in data["assets"] if a["role"] not in ("product", "look")),
        "look_lock": creative["look"], "art_direction_lock": creative.get("scene_design", creative["concept"]),
        "layout_and_spatial_relationships": "\n".join(x["rationale"] for x in data["layouts"]),
        "product_identity_lock": creative["identity"], "supported_product_states": creative["product_facts"],
        "product_material_and_structure_rules": "未知信息：" + (creative["unknowns"] or "未额外推断未知结构或作用。"),
        "packaging_text_and_layout": creative["text_lock"],
        "text_visibility_windows": creative.get("visibility", "文字附着真实表面，阅读窗口兼顾字号、相对速度和反光；未知小字不猜写。"),
        "camera_system": creative["photography"],
        "motion_and_framing_rules": "保持预演的真实纵深路径、机位朝向和主体画面占比变化；相机与主体运动分别执行。",
        "lighting_system": creative["lighting"],
        "lighting_constraints_and_material_response": "最终光影与料体按本文设计及产品/影调参考实现，预演中性外观不作为最终外观依据。",
        "material_process": creative["material_process"],
        "previs_use_rules": creative.get("previs_rules", "简化几何只承担占位与运动，不能覆盖产品图事实。"),
        "unimplemented_appearance_instructions": "按本文的料体物性与动态光影设计完成最终画面；预演中的几何占位只限定空间与运动关系。",
        "endcard_entry_and_completion": "主要入场、景别变化、主体姿态和品牌信息全部落位后再开始停留。",
        "hold_start_seconds": n(data["hold_start"] / fps),
        "stable_hold_description": "保持构图、主姿态与品牌信息稳定，余动不妨碍阅读。",
    }
    shot_blocks = []
    for shot, measured in zip(data["shots"], report["shots"]):
        lenses = [s["lens_mm"] for s in measured["samples"]]
        lens_text = n(min(lenses)) if min(lenses) == max(lenses) else f"{n(min(lenses))}—{n(max(lenses))}"
        layout = next(x for x in data["layouts"] if x["id"] == shot["layout"])
        local_values = dict(global_values, shot_id=shot["id"], shot_start_seconds=n(shot["start"]/fps),
                            shot_end_seconds=n(shot["end"]/fps),
                            shot_lens_and_sensor=f"{lens_text}mm；传感器宽{n(shot['camera']['sensor_width_mm'])}mm。",
                            shot_viewpoint_and_framing=shot["purpose"], shot_attention_and_entry_state=shot["entry_state"],
                            shot_camera_path_target_and_speed=shot["narrative"]["camera"] + "\n" + measured_camera_text(shot, measured, layout),
                            shot_product_material_and_set_action=shot["narrative"]["subject"] + "\n" + shot["narrative"]["material"],
                            shot_light_shape_path_timing_and_response=shot["narrative"]["light"],
                            shot_reading_window="按本镜主信息保留需要的辨认窗口，真实透视和表面附着关系持续成立。",
                            shot_exit_cut_basis_and_next_entry=shot["exit_state"] + "\n" + shot["narrative"]["cut"])
        shot_blocks.append(expand_template(shot_template, local_values))
    return (expand_template(template[:start], global_values) + "".join(shot_blocks)
            + expand_template(template[end:], global_values)).strip() + "\n"


def compile_prompt(lane, allow_unreviewed=False, limit=None, reserve=0):
    checks = inspect(lane)
    lane, data, manifest, report = checked_backend(lane)
    review_path = lane / "visual-review.json"
    reviewed = False
    if review_path.exists():
        record = read_json(review_path)
        reviewed = record.get("binding") == checks["binding"] and record.get("status") == "pass"
    if not reviewed and not allow_unreviewed:
        raise ContractError("Complete actual playback and layout comparison, then record review; or explicitly compile an unreviewed draft")
    if type(reserve) is not int or reserve < 0 or (limit is not None and (type(limit) is not int or limit <= reserve)):
        raise ContractError("Invalid character limit/reserve")
    fps = data["fps"]
    technical = []
    for shot, measured in zip(data["shots"], report["shots"]):
        samples = measured["samples"]
        a, b = samples[0], samples[-1]
        heights = [s["bbox"][3] - s["bbox"][1] for s in samples]
        lens = sorted(set(round(float(s["lens_mm"]), 2) for s in samples))
        technical.append({"id": shot["id"], "seconds": [shot["start"]/fps, shot["end"]/fps],
                          "layout": shot["layout"], "lens_mm_range": [min(lens), max(lens)],
                          "camera_start": a["camera_position"], "camera_end": b["camera_position"],
                          "height_fraction_range": [min(heights), max(heights)],
                          "measured_motion": "camera and proxy transform samples in backend-report.json",
                          "authored_design_only": ["lighting", "fluid/material response"],
                          "semantic_reconciliation": "Agent must compare narrative against full measured path and playback"})
    prompt = render_prompt(data, report)
    counts = {"codepoints": len(prompt), "utf16": len(prompt.encode("utf-16-le")) // 2}
    if limit is not None and max(counts.values()) > limit - reserve:
        raise ContractError(f"Prompt exceeds limit/reserve: {counts}; edit authored text without dropping locked content")
    delivery = lane / "delivery"
    no_overwrite(delivery)
    delivery.mkdir()
    (delivery / "prompt.md").write_text(prompt, encoding="utf-8")
    attachments = [{"id": a["id"], "role": a["role"], "path": str(safe_path(lane, a["path"], True)),
                    "sha256": a["sha256"], "platform_label": None} for a in data["assets"]]
    for item in read_json(lane / "media-report.json")["clips"]:
        attachments.append({"id": f"PREVIS-{item['id']}", "role": "motion_and_timing",
                            "path": item["path"], "sha256": item["sha256"], "platform_label": None})
    dump_json(delivery / "attachments.json", {"status": "neutral_material_roles", "provider": data["provider"],
               "submission_performed": False, "generation_units": None,
               "note": "Shots are not generation units. Verify the actual entry and map roles before submission.",
               "assets": attachments})
    dump_json(delivery / "measured-shot-summary.json", technical)
    result = {"schema": "product-tvc-delivery/v1", "version": VERSION, "fixture": data["fixture"],
              "status": "reviewed_previs_prompt" if reviewed else "unreviewed_draft",
              "counts": counts, "limit": limit, "reserve": reserve, "binding": checks["binding"],
              "prompt_sha256": sha256_file(delivery / "prompt.md"),
              "template_sha256": sha256_file(PACKAGE / "assets" / "prompt-template.md"),
              "compiler_sha256": sha256_file(Path(__file__)),
              "generated_layout_quality": "fixture_only" if data["fixture"] else "requires_authored_image_review",
              "final_video_generation": "not_run", "user_acceptance": "not_implied"}
    dump_json(delivery / "delivery.json", result)
    return {"delivery": str(delivery), "status": result["status"], "counts": counts}


def check_prompt_attachments(prompt, available, mapped, unit_id):
    """Check explicit reference tokens, not the meaning of unlabelled prose."""
    def mentioned(token):
        return re.search(r"(?<![A-Za-z0-9_-])" + re.escape(token) + r"(?![A-Za-z0-9_-])", prompt) is not None

    neutral_ids = {asset_id for asset_id in available if mentioned(asset_id)}
    # PREVIS is a reserved attachment namespace. Also catch misspelled/nonexistent
    # IDs, rather than only looking for IDs that happen to be in the inventory.
    neutral_ids.update(re.findall(r"(?<![A-Za-z0-9_-])PREVIS-[A-Za-z0-9_-]+", prompt))
    aliases = {item["platform_label"]: item["id"] for item in mapped if item["platform_label"] is not None}
    conventional_labels = set(re.findall(
        r"(?<![A-Za-z0-9_@-])@(?:图片|视频|音频|image|video|audio)[0-9]+(?![A-Za-z0-9_-])", prompt))
    unknown_labels = conventional_labels - set(aliases)
    referenced_ids = neutral_ids | {asset_id for label, asset_id in aliases.items() if mentioned(label)}
    mapped_ids = {item["id"] for item in mapped}
    missing = referenced_ids - mapped_ids
    unused = mapped_ids - referenced_ids
    if missing or unused or unknown_labels:
        raise ContractError(
            f"Unit {unit_id} prompt/attachment mismatch: "
            f"unmapped references={sorted(missing)}, "
            f"attachments absent from prompt={sorted(unused)}, "
            f"unmapped platform labels={sorted(unknown_labels)}")
    return sorted(referenced_ids)


def finalize(lane, edits_path, out=None):
    """Bind authored final text/optional verified platform mapping to unchanged actual media."""
    checked = inspect(lane)
    lane, data, manifest, report = checked_backend(lane)
    edits_path = Path(edits_path).resolve()
    edits = read_json(edits_path)
    if edits.get("schema") != "product-tvc-final-text/v1" or edits.get("binding") != checked["binding"]:
        raise ContractError("Final text must bind the current complete media set")
    if not isinstance(edits.get("semantic_review"), str) or not edits["semantic_review"].strip():
        raise ContractError("Final text requires authored reconciliation against actual motion, states and timing")
    provider = edits.get("provider", data["provider"])
    verified = provider.get("status") == "verified"
    if provider.get("status") not in ("unverified", "verified"):
        raise ContractError("Provider status must be unverified or verified")
    if verified:
        for field in ("name", "entry", "checked_at", "evidence"):
            if not isinstance(provider.get(field), str) or not provider[field].strip():
                raise ContractError(f"Verified platform mapping requires {field}")
        if type(provider.get("max_seconds")) not in (int,float) or not math.isfinite(provider["max_seconds"]) or provider["max_seconds"] <= 0:
            raise ContractError("Verified platform requires a positive known duration limit")
        if type(provider.get("max_images")) is not int or provider["max_images"] < 0 or type(provider.get("supports_video_reference")) is not bool:
            raise ContractError("Verified platform requires known image/video-reference capability")
    available = {a["id"]: {"path": str(safe_path(lane, a["path"], True)), "sha256": a["sha256"], "role": a["role"]}
                 for a in data["assets"]}
    media = read_json(lane / "media-report.json")
    for clip in media["clips"]:
        available["PREVIS-" + clip["id"]] = dict(clip, role="motion_and_timing")
    available["PREVIS-FULL"] = dict(media["full"], role="motion_and_timing")
    units = edits.get("units")
    if not isinstance(units, list) or not units:
        raise ContractError("Final text needs at least one generation/delivery unit")
    cursor, seen, prepared = 0, set(), []
    for unit in units:
        unit_id = unit.get("id")
        if not isinstance(unit_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", unit_id) or unit_id.casefold() in seen:
            raise ContractError("Unit IDs must be unique safe identifiers")
        seen.add(unit_id.casefold())
        if type(unit.get("start")) is not int or type(unit.get("end")) is not int or unit["start"] != cursor or unit["end"] <= cursor:
            raise ContractError("Final units must exactly and continuously cover the timeline")
        cursor = unit["end"]
        expected_shots = [s["id"] for s in data["shots"] if s["start"] < unit["end"] and s["end"] > unit["start"]]
        if unit.get("shot_ids") != expected_shots:
            raise ContractError(f"Unit {unit_id} shot coverage differs from actual timeline")
        for field in ("entry_state", "exit_state"):
            if not isinstance(unit.get(field), str) or not unit[field].strip():
                raise ContractError(f"Unit {unit_id} requires its own {field}")
        text_path = safe_path(edits_path.parent, unit.get("prompt_path"), True)
        prompt = text_path.read_text(encoding="utf-8-sig")
        if not prompt.strip() or re.search(r"\{\{[a-z_]+\}\}", prompt):
            raise ContractError(f"Unit {unit_id} has empty or unfilled prompt text")
        counts = {"codepoints": len(prompt), "utf16": len(prompt.encode("utf-16-le")) // 2}
        limit, reserve = unit.get("limit"), unit.get("reserve", 0)
        count_unit = unit.get("count_unit", "both")
        if count_unit not in ("codepoints", "utf16", "both") or type(reserve) is not int or reserve < 0:
            raise ContractError("Invalid unit counting policy")
        if limit is not None:
            if type(limit) is not int or limit <= reserve:
                raise ContractError("Invalid unit character limit")
            count = max(counts.values()) if count_unit == "both" else counts[count_unit]
            if count > limit - reserve:
                raise ContractError(f"Final unit {unit_id} exceeds its text limit: {counts}")
        mapped = []
        labels = set()
        attachment_ids = set()
        for mapping in unit.get("attachments", []):
            asset_id = mapping.get("id")
            if asset_id not in available or asset_id in attachment_ids:
                raise ContractError(f"Invalid/duplicate attachment reference in {unit_id}: {asset_id}")
            attachment_ids.add(asset_id)
            asset = available[asset_id]
            if mapping.get("sha256") != asset["sha256"]:
                raise ContractError(f"Attachment hash mismatch: {asset_id}")
            upload = mapping.get("upload", False)
            label = mapping.get("platform_label")
            if type(upload) is not bool:
                raise ContractError("Attachment upload is a proposed boolean, never a performed action")
            if not verified and (upload or label is not None):
                raise ContractError("Unverified platform must retain neutral material roles without upload labels")
            if not upload and label is not None:
                raise ContractError("Attachments without proposed upload must retain neutral IDs and no platform label")
            if upload:
                if not isinstance(label, str) or not label.strip() or label in labels:
                    raise ContractError("Proposed platform upload needs unique verified labels per unit")
                if label in available:
                    raise ContractError("Platform labels must not collide with neutral attachment IDs")
                labels.add(label)
                if asset["role"] == "motion_and_timing" and not provider["supports_video_reference"]:
                    raise ContractError("Platform evidence does not support video-reference input")
            if not isinstance(mapping.get("purpose"), str) or not mapping["purpose"].strip():
                raise ContractError("Every final attachment requires an explicit purpose")
            mapped.append(dict(asset, id=asset_id, upload=upload, platform_label=label, purpose=mapping["purpose"]))
        if verified:
            if (unit["end"] - unit["start"]) / data["fps"] > provider["max_seconds"]:
                raise ContractError(f"Unit {unit_id} exceeds verified duration capability")
            if sum(x["upload"] and x["role"] != "motion_and_timing" for x in mapped) > provider["max_images"]:
                raise ContractError(f"Unit {unit_id} exceeds verified image-reference count")
        referenced_ids = check_prompt_attachments(prompt, available, mapped, unit_id)
        prepared.append((unit, prompt, counts, mapped, referenced_ids))
    if cursor != data["duration_frames"]:
        raise ContractError("Final units do not cover the full actual timeline")
    target = inside(lane, out or lane / "finalized-delivery")
    no_overwrite(target)
    target.mkdir(parents=True)
    records = []
    for unit, prompt, counts, mapped, referenced_ids in prepared:
        path = target / f"{unit['id']}.md"
        path.write_text(prompt, encoding="utf-8")
        records.append({k:v for k,v in unit.items() if k not in ("prompt_path", "attachments")} |
                       {"prompt": path.name, "prompt_sha256": sha256_file(path), "counts": counts,
                        "attachments": mapped, "prompt_attachment_ids": referenced_ids})
    reviewed = False
    if (lane / "visual-review.json").exists():
        visual = read_json(lane / "visual-review.json")
        reviewed = visual.get("binding") == checked["binding"] and visual.get("status") == "pass"
    result = {"schema": "product-tvc-final-delivery/v1", "version": VERSION, "created_at": now(),
              "finalizer_package_files": package_hashes(),
              "fixture": data["fixture"], "binding": checked["binding"], "provider": provider,
              "semantic_review": edits["semantic_review"], "units": records,
              "status": "finalized_text" if reviewed else "finalized_text_pending_playback",
              "submission_performed": False, "user_acceptance": "not_implied"}
    dump_json(target / "delivery.json", result)
    return {"delivery": str(target), "units": len(records), "status": result["status"]}


def status(lane):
    lane = Path(lane).resolve()
    result = {}
    for mode in ("layout", "build", "inspect"):
        dispatch = lane / f"{mode}-dispatch.json"
        log = lane / f"{mode}-console.log"
        item = {"dispatched": dispatch.exists()}
        if dispatch.exists():
            item.update(read_json(dispatch))
        if log.exists():
            item["log_bytes"] = log.stat().st_size
            item["tail"] = log.read_text(encoding="utf-8", errors="replace")[-1500:]
        result[mode] = item
    result["artifacts"] = {p: (lane / p).exists() for p in ("backend-report.json", "scene.blend", "reopen.json", "media-report.json", "worker-result.json")}
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    p = commands.add_parser("fixture"); p.add_argument("--out", required=True)
    p = commands.add_parser("validate"); p.add_argument("contract")
    p = commands.add_parser("prepare"); p.add_argument("contract"); p.add_argument("--out", required=True); p.add_argument("--lane", required=True); p.add_argument("--mode", choices=("layout","build"), default="build"); p.add_argument("--layout-review")
    p = commands.add_parser("assemble"); p.add_argument("lane"); p.add_argument("--ffmpeg", default="ffmpeg"); p.add_argument("--ffprobe", default="ffprobe")
    for name in ("inspect", "status", "reopen-request"):
        p = commands.add_parser(name); p.add_argument("lane")
    p = commands.add_parser("compile"); p.add_argument("lane"); p.add_argument("--allow-unreviewed", action="store_true"); p.add_argument("--limit", type=int); p.add_argument("--reserve", type=int, default=0)
    p = commands.add_parser("review"); p.add_argument("lane"); p.add_argument("--review", required=True)
    p = commands.add_parser("finalize"); p.add_argument("lane"); p.add_argument("--edits", required=True); p.add_argument("--out")
    args = parser.parse_args(argv)
    try:
        if args.command == "fixture": result = {"contract": str(create_fixture(args.out))}
        elif args.command == "validate":
            data = load_contract(args.contract); result = {"valid": True, "sha256": contract_digest(data), "shots": len(data["shots"]), "fixture": data["fixture"]}
        elif args.command == "prepare": result = prepare(args.contract, args.out, args.lane, args.mode, args.layout_review)
        elif args.command == "assemble": result = assemble(args.lane, args.ffmpeg, args.ffprobe)
        elif args.command == "inspect": result = inspect(args.lane)
        elif args.command == "reopen-request":
            checked_backend(args.lane); mcp_request(args.lane, "inspect"); result = {"mcp_request": str(Path(args.lane).resolve() / "mcp-inspect.json")}
        elif args.command == "review": result = review(args.lane, args.review)
        elif args.command == "finalize": result = finalize(args.lane, args.edits, args.out)
        elif args.command == "compile": result = compile_prompt(args.lane, args.allow_unreviewed, args.limit, args.reserve)
        else: result = status(args.lane)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ContractError, OSError, KeyError, TypeError, ValueError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
