#!/usr/bin/env python3
"""Build and inspect a portable, geometry-only product previs in background Blender.

Invoke through the available background Blender MCP, or an explicitly authorized
background process::

    blender --background --factory-startup --python blender_worker.py -- JOB.json
    blender --background LANE/scene.blend --python blender_worker.py -- INSPECT.json

The worker never opens a browser, loads customer geometry, uploads, or starts a
second process. All writes stay in the prepared lane. A started build is immutable:
after a failed build prepare a new lane, rather than racing another writer.
"""

from __future__ import annotations

import importlib.util
import json
import math
import os
from pathlib import Path
import sys
import time
import traceback
from typing import Any


REPORT_SCHEMA = "product-tvc-backend/v1"
SAMPLE_STEP = 0.5
TRANSFORM_TOLERANCE = 3e-5  # Blender stores animation channels in float32.
VISIBILITY_GRID = 7
LIMITATIONS = [
    "Workbench studio shading is a geometry preview; authored lighting, optical materials, and fluids are unverified.",
    "Product primitives prove occupancy and transforms, not real silhouette, mechanisms, label accuracy, or text readability.",
    "Visibility uses a 7 x 7 ray sample of the designated proxy's projected silhouette, including frame crop.",
    "Camera clearance is checked at integer and midpoint samples; it is not continuous collision detection.",
    "Technical readback does not establish layout-image agreement, full-speed visual quality, or downstream video-model compliance.",
]


class WorkerError(ValueError):
    """A job cannot safely produce or substantiate the requested artifacts."""


def _core():
    # Resolve only the helper shipped in this independently installable package.
    path = Path(__file__).resolve().with_name("core.py")
    spec = importlib.util.spec_from_file_location("_product_tvc_previs_worker_core", path)
    if spec is None or spec.loader is None:
        raise WorkerError("Cannot load this package's core.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _blender():
    global bpy, bmesh, Vector, Matrix, Quaternion, Euler, world_to_camera_view
    try:
        import bpy
        import bmesh
        from mathutils import Vector, Matrix, Quaternion, Euler
        from bpy_extras.object_utils import world_to_camera_view
    except ImportError as exc:
        raise WorkerError("This worker must run inside background Blender") from exc
    if not bpy.app.background:
        raise WorkerError("Desktop Blender execution is outside this worker's contract")


def _finite(value: Any, context: str) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            _finite(item, f"{context}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _finite(item, f"{context}[{index}]")
    elif isinstance(value, (int, float)) and not math.isfinite(value):
        raise WorkerError(f"Nonfinite value at {context}")


def _read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise WorkerError(f"Expected an object in {path.name}")
    _finite(value, path.name)
    return value


def _job(job_path: str | Path):
    core = _core()
    supplied = Path(job_path)
    if not supplied.is_absolute():
        raise WorkerError("job_path must be absolute")
    path = supplied.resolve(strict=True)
    job = _read_json(path)
    if job.get("schema") != "product-tvc-job/v1":
        raise WorkerError("Unsupported job schema")
    if job.get("mode") not in {"layout", "build", "inspect"}:
        raise WorkerError("mode must be layout, build or inspect")
    if not isinstance(job.get("lane_root"), str) or not Path(job["lane_root"]).is_absolute():
        raise WorkerError("lane_root must be an absolute path")
    lane = Path(job["lane_root"]).resolve(strict=True)
    if not lane.is_dir() or lane == Path(lane.anchor):
        raise WorkerError("lane_root must be a prepared, non-root directory")
    try:
        relative = path.relative_to(lane)
    except ValueError as exc:
        raise WorkerError("Job must be inside its lane") from exc
    core.safe_path(lane, relative.as_posix(), must_exist=True)
    contract_path = job.get("contract_path")
    if not isinstance(contract_path, str) or not Path(contract_path).is_absolute():
        raise WorkerError("contract_path must be absolute")
    contract_path = Path(contract_path).resolve(strict=True)
    expected = core.safe_path(lane, "scene.json", must_exist=True)
    if contract_path != expected:
        raise WorkerError("Build input must be the lane's canonical scene.json")
    contract = core.load_contract(contract_path, verify_assets=True)
    digest = core.contract_digest(contract)
    if job.get("contract_sha256") != digest:
        raise WorkerError("Job contract_sha256 does not match the canonical contract")
    inputs = core.safe_path(lane, "inputs", must_exist=True)
    if not inputs.is_dir():
        raise WorkerError("Prepared lane must contain its own inputs directory")
    for asset in contract["assets"]:
        asset_path = core.safe_path(lane, asset["path"], must_exist=True)
        try:
            asset_path.relative_to(inputs)
        except ValueError as exc:
            raise WorkerError("Prepared assets must be copied under lane/inputs") from exc
    return core, job, lane, contract


def _out(core, lane: Path, relative: str) -> Path:
    path = core.safe_path(lane, relative, must_exist=False)
    if relative == "scene.json" or relative.replace("\\", "/").split("/")[0] == "inputs":
        raise WorkerError("Input files are read-only")
    path.parent.mkdir(parents=True, exist_ok=True)
    # Recheck after creating parents, including symlinks in existing parents.
    return core.safe_path(lane, relative, must_exist=False)


def _write(core, lane: Path, relative: str, data: dict) -> None:
    _finite(data, relative)
    path = _out(core, lane, relative)
    temp = _out(core, lane, f"{relative}.{os.getpid()}.tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    os.replace(temp, path)


def _log(core, lane: Path, message: str) -> None:
    path = _out(core, lane, "worker.log")
    stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"{stamp} pid={os.getpid()} {message}\n")
    print(message, flush=True)


def _claim(core, lane: Path, job: dict) -> None:
    path = _out(core, lane, f"execution/{job['mode']}-started.json")
    marker = {"mode": job["mode"], "worker_pid": os.getpid(), "started_at": time.time(),
              "contract_sha256": job["contract_sha256"], "argv": sys.argv}
    try:
        with path.open("x", encoding="utf-8") as handle:
            json.dump(marker, handle, ensure_ascii=False, indent=2)
    except FileExistsError as exc:
        raise WorkerError(f"This lane's {job['mode']} was already started; do not duplicate its writer") from exc


def _context(scene):
    if bpy.context.window is not None:
        bpy.context.window.scene = scene
    with bpy.context.temp_override(scene=scene, view_layer=scene.view_layers[0]):
        scene.view_layers[0].update()
        return bpy.context.evaluated_depsgraph_get()


def _frame(scene, local_frame: float):
    value = 1.0 + local_frame
    whole = math.floor(value)
    scene.frame_set(whole, subframe=value - whole)
    return _context(scene)


def _times(frames: int) -> list[float]:
    return [index * SAMPLE_STEP for index in range(frames * 2 - 1)]


def _new_scene(name: str, contract: dict, frames: int):
    scene = bpy.data.scenes.new(name)
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x, scene.render.resolution_y = contract["resolution"]
    scene.render.resolution_percentage = 100
    scene.render.pixel_aspect_x = scene.render.pixel_aspect_y = 1.0
    scene.render.fps = contract["fps"]
    scene.render.fps_base = 1.0
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.image_settings.color_depth = "8"
    scene.render.film_transparent = False
    scene.render.use_file_extension = True
    # Embed fixture identity in the media itself, using Blender's bundled font.
    # Production renders remain free of debug overlays.
    scene.render.use_stamp = bool(contract["fixture"])
    for prop in scene.render.bl_rna.properties:
        if prop.identifier.startswith("use_stamp_") and prop.type == "BOOLEAN" and not prop.is_readonly:
            setattr(scene.render, prop.identifier, False)
    if contract["fixture"]:
        scene.render.use_stamp_note = True
        scene.render.stamp_note_text = "TECHNICAL FIXTURE - PROXY ONLY"
        scene.render.stamp_font_size = 10
        scene.render.stamp_foreground = (1.0, 1.0, 1.0, 1.0)
        scene.render.stamp_background = (0.0, 0.0, 0.0, 0.65)
    scene.frame_start, scene.frame_end = 1, frames
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "OBJECT"
    scene.display.shading.background_type = "WORLD"
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = "BOTH"
    scene.display.shading.show_specular_highlight = False
    scene.display.render_aa = "8"
    scene.world = bpy.data.worlds.new(f"{name}__preview_world")
    scene.world.color = (0.32, 0.32, 0.32)
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.exposure = 0.0
    scene.view_settings.gamma = 1.0
    scene["previs_contract_sha256"] = contract["_digest"]
    scene["previs_geometry_only"] = True
    _context(scene)
    return scene


def _mesh(spec: dict, name: str):
    mesh = bpy.data.meshes.new(name)
    if spec["primitive"] == "mesh":
        low = [min(vertex[axis] for vertex in spec["vertices"]) for axis in range(3)]
        high = [max(vertex[axis] for vertex in spec["vertices"]) for axis in range(3)]
        vertices = [[(vertex[axis] - (low[axis] + high[axis]) * .5) / (high[axis] - low[axis])
                     if high[axis] - low[axis] > 1e-12 else 0.0 for axis in range(3)] for vertex in spec["vertices"]]
        mesh.from_pydata(vertices, [], spec["faces"])
        edges = {}
        for face in spec["faces"]:
            for a, b in zip(face, face[1:] + face[:1]):
                edge = tuple(sorted((a, b)))
                edges[edge] = edges.get(edge, 0) + 1
        mesh["previs_closed"] = bool(edges) and all(count == 2 for count in edges.values())
        mesh["previs_zero_extent_axes"] = [axis for axis in range(3) if high[axis] - low[axis] <= 1e-12]
    elif spec["primitive"] == "plane":
        mesh.from_pydata([(-.5, -.5, 0), (.5, -.5, 0), (.5, .5, 0), (-.5, .5, 0)], [], [(0, 1, 2, 3)])
    else:
        bm = bmesh.new()
        try:
            if spec["primitive"] == "cube":
                bmesh.ops.create_cube(bm, size=1.0)
            elif spec["primitive"] == "sphere":
                bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=16, radius=0.5)
            elif spec["primitive"] == "cylinder":
                bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=32, radius1=.5, radius2=.5, depth=1.0)
            else:
                raise WorkerError(f"Unsupported primitive: {spec['primitive']}")
            bm.to_mesh(mesh)
        finally:
            bm.free()
    mesh.update()
    return mesh


def _object(scene, spec: dict, mesh, layout_id: str):
    obj = bpy.data.objects.new(f"{scene.name}__{spec['id']}", mesh)
    scene.collection.objects.link(obj)
    obj["previs_object_id"] = spec["id"]
    obj["previs_layout_id"] = layout_id
    obj["previs_primitive"] = spec["primitive"]
    obj["previs_base_dimensions"] = spec["dimensions"]
    obj["previs_role"] = spec["role"]
    obj.rotation_mode = "QUATERNION"
    obj.location = spec["location"]
    obj.rotation_quaternion = Euler([math.radians(value) for value in spec["rotation_deg"]], "XYZ").to_quaternion()
    obj.scale = spec["dimensions"]
    obj.color = (*spec["color"], 1.0)
    return obj


def _camera(scene, spec: dict, extent: float):
    data = bpy.data.cameras.new(f"{scene.name}__optics")
    obj = bpy.data.objects.new(f"{scene.name}__camera", data)
    scene.collection.objects.link(obj)
    scene.camera = obj
    obj.rotation_mode = "QUATERNION"
    data.type = "PERSP"
    data.sensor_fit = "HORIZONTAL"
    _camera_number(data, "sensor_width", spec["sensor_width_mm"])
    data.clip_start = max(1e-5, extent * 1e-4)
    data.clip_end = max(1000.0, extent * 10000.0)
    data.dof.use_dof = False
    return obj


def _camera_number(data, name: str, value: float) -> None:
    """Reject Blender's silent numeric clamping instead of reporting it as intent."""
    _finite(value, f"camera.{name}")
    prop = data.bl_rna.properties[name]
    if not prop.hard_min <= value <= prop.hard_max:
        raise WorkerError(f"camera.{name}={value} is outside this Blender version's supported range [{prop.hard_min}, {prop.hard_max}]")
    setattr(data, name, value)


def _orientation(position, target, roll_deg=0.0, prior_up=None, prior_quaternion=None):
    forward = Vector(target) - Vector(position)
    if forward.length < 1e-8:
        raise WorkerError("Camera position and target coincide")
    forward.normalize()
    # Preserve a level horizon where defined. At a pole transport the prior up;
    # select its continuous sign on exiting the pole instead of flipping 180 deg.
    reference = Vector((0.0, 0.0, 1.0))
    up = reference - forward * reference.dot(forward)
    if up.length < 1e-4 and prior_up is not None:
        reference = Vector(prior_up)
        up = reference - forward * reference.dot(forward)
    if up.length < 1e-6:
        reference = min((Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))), key=lambda value: abs(value.dot(forward)))
        up = reference - forward * reference.dot(forward)
    up.normalize()
    if prior_up is not None and up.dot(Vector(prior_up)) < 0:
        up.negate()
    right = forward.cross(up).normalized()
    up = right.cross(forward).normalized()
    base = Matrix((right, up, -forward)).transposed().to_quaternion().normalized()
    quaternion = (base @ Quaternion((0, 0, 1), math.radians(roll_deg))).normalized()
    if prior_quaternion is not None and quaternion.dot(Quaternion(prior_quaternion)) < 0:
        quaternion.negate()
    return quaternion, up


def _set_pose(obj, spec: dict, animation: dict | None, frame: float, core):
    if animation is None:
        values = {"location": spec["location"], "rotation_deg": spec["rotation_deg"], "scale": [1, 1, 1]}
    else:
        values = core.interpolate_keys(animation["keys"], frame, mode=animation.get("interpolation", "hermite"), endpoint_mode=animation.get("endpoint_mode", "continue"))
    _finite(values, f"object.{spec['id']}@{frame}")
    if any(value <= 0 for value in values["scale"]):
        raise WorkerError(f"Interpolated nonpositive scale for {spec['id']} at {frame}")
    obj.location = values["location"]
    obj.rotation_quaternion = Euler([math.radians(value) for value in values["rotation_deg"]], "XYZ").to_quaternion()
    obj.scale = [base * multiplier for base, multiplier in zip(spec["dimensions"], values["scale"])]


def _world_corners(obj):
    return [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]


def _projection(scene, camera, obj):
    projected = [world_to_camera_view(scene, camera, point) for point in _world_corners(obj)]
    values = [component for point in projected for component in point]
    _finite(values, "bbox_projection")
    return [min(point.x for point in projected), min(point.y for point in projected),
            max(point.x for point in projected), max(point.y for point in projected)], [point.z for point in projected]


def _fit(scene, camera, obj, key: dict):
    fit = key["fit"]
    target = Vector(key["target"]) + Vector(fit["target_offset"])
    azimuth, elevation = map(math.radians, (fit["azimuth_deg"], fit["elevation_deg"]))
    direction = Vector((math.sin(azimuth) * math.cos(elevation), -math.cos(azimuth) * math.cos(elevation), math.sin(elevation)))
    _camera_number(camera.data, "lens", key["lens_mm"])
    quaternion, _ = _orientation(target + direction, target, key["roll_deg"])
    camera.rotation_quaternion = quaternion
    corners = _world_corners(obj)
    radius = max((point - target).length for point in corners)
    # Ensure the entire actual bounding box lies in front of the near plane.
    low = max((point - target).dot(direction) for point in corners) + max(radius * 1e-6, camera.data.clip_start * 2)
    low = max(low, camera.data.clip_start * 2)

    def height(distance):
        camera.location = target + direction * distance
        _context(scene)
        bbox, depths = _projection(scene, camera, obj)
        if min(depths) <= camera.data.clip_start:
            return math.inf
        return bbox[3] - bbox[1]

    wanted = fit["height_fraction"]
    if height(low) < wanted:
        raise WorkerError("Requested fit cannot be reached while retaining positive camera depth")
    high = max(low * 2.0, radius * 2.0, 1e-3)
    for _ in range(64):
        if height(high) <= wanted:
            break
        high *= 2
    else:
        raise WorkerError("Could not bracket camera fit")
    for _ in range(56):
        middle = (low + high) * .5
        if height(middle) > wanted:
            low = middle
        else:
            high = middle
    distance = (low + high) * .5
    actual_height = height(distance)
    if abs(actual_height - wanted) > max(2e-5, wanted * 2e-5):
        raise WorkerError("Bounding-box camera fit did not converge")
    return list(target + direction * distance), list(target), {"frame": key["frame"], "object": fit["object"],
        "requested_height": wanted, "actual_height": actual_height, "distance": distance,
        "position": list(camera.location), "method": "actual_bbox_projected_height_bisection"}


def _resolve_camera(scene, camera, camera_spec: dict, objects: dict, specs: dict, animations: dict, core):
    resolved, fits = [], []
    for key in camera_spec["keys"]:
        for object_id, obj in objects.items():
            _set_pose(obj, specs[object_id], animations.get(object_id), key["frame"], core)
        _context(scene)
        value = {name: data for name, data in key.items() if name != "fit"}
        if "fit" in key:
            position, target, evidence = _fit(scene, camera, objects[key["fit"]["object"]], key)
            value["position"], value["target"] = position, target
            fits.append(evidence)
        resolved.append(value)
    return resolved, fits


def _fcurves(id_block):
    animation = id_block.animation_data
    if animation is None or animation.action is None:
        return []
    action = animation.action
    curves, seen = [], set()
    for layer in getattr(action, "layers", []):
        for strip in layer.strips:
            for channelbag in getattr(strip, "channelbags", []):
                for curve in channelbag.fcurves:
                    if curve.as_pointer() not in seen:
                        seen.add(curve.as_pointer())
                        curves.append(curve)
    # Legacy files/versions may expose direct F-curves instead.
    if not curves:
        for curve in getattr(action, "fcurves", []):
            if curve.as_pointer() not in seen:
                seen.add(curve.as_pointer())
                curves.append(curve)
    return curves


def _linear(id_block):
    curves = _fcurves(id_block)
    if not curves:
        raise WorkerError(f"No animation curves after baking {id_block.name}")
    for curve in curves:
        curve.extrapolation = "CONSTANT"
        for point in curve.keyframe_points:
            point.interpolation = "LINEAR"
        curve.update()
    return sum(len(curve.keyframe_points) for curve in curves)


def _check_linear(id_blocks):
    curve_count = key_count = 0
    for block in id_blocks:
        curves = _fcurves(block)
        if not curves:
            raise WorkerError(f"Saved scene is missing animation for {block.name}")
        for curve in curves:
            curve_count += 1
            if curve.modifiers or curve.extrapolation != "CONSTANT":
                raise WorkerError("Unexpected modifier/extrapolation on a baked F-curve")
            for point in curve.keyframe_points:
                key_count += 1
                if point.interpolation != "LINEAR":
                    raise WorkerError("Saved animation contains a non-LINEAR baked key")
    return {"fcurves": curve_count, "keys": key_count, "interpolation": "LINEAR", "bake_step_frames": SAMPLE_STEP}


def _bake(scene, shot: dict, layout: dict, objects: dict, camera, core):
    specs = {item["id"]: item for item in layout["objects"]}
    animations = {item["object"]: item for item in shot["animations"]}
    resolved, fits = _resolve_camera(scene, camera, shot["camera"], objects, specs, animations, core)
    expected = []
    prior_up = prior_camera = None
    prior_objects = {}
    for frame in _times(shot["end"] - shot["start"]):
        values = core.interpolate_keys(resolved, frame, mode=shot["camera"].get("interpolation", "hermite"), endpoint_mode=shot["camera"].get("endpoint_mode", "continue"))
        _finite(values, f"camera.{shot['id']}@{frame}")
        if values["lens_mm"] <= 0:
            raise WorkerError("Camera interpolation produced a nonpositive lens")
        camera.location = values["position"]
        camera.rotation_quaternion, prior_up = _orientation(values["position"], values["target"], values["roll_deg"], prior_up, prior_camera)
        prior_camera = camera.rotation_quaternion.copy()
        _camera_number(camera.data, "lens", values["lens_mm"])
        blender_frame = frame + 1.0
        camera.keyframe_insert("location", frame=blender_frame)
        camera.keyframe_insert("rotation_quaternion", frame=blender_frame)
        camera.data.keyframe_insert("lens", frame=blender_frame)
        object_states = {}
        for object_id, obj in objects.items():
            _set_pose(obj, specs[object_id], animations.get(object_id), frame, core)
            if object_id in prior_objects and obj.rotation_quaternion.dot(prior_objects[object_id]) < 0:
                obj.rotation_quaternion.negate()
            prior_objects[object_id] = obj.rotation_quaternion.copy()
            for prop in ("location", "rotation_quaternion", "scale"):
                obj.keyframe_insert(prop, frame=blender_frame)
            object_states[object_id] = {"location": list(obj.location), "quaternion": list(obj.rotation_quaternion.normalized()), "scale": list(obj.scale)}
        expected.append({"frame": frame, "camera_position": list(camera.location),
            "camera_quaternion": list(camera.rotation_quaternion.normalized()), "lens_mm": float(camera.data.lens), "objects": object_states})
    for block in [camera, camera.data, *objects.values()]:
        _linear(block)
    scene["previs_camera_keys"] = json.dumps(resolved, allow_nan=False)
    scene["previs_camera_interpolation"] = shot["camera"].get("interpolation", "hermite")
    return expected, fits


def _visibility(scene, camera, target, depsgraph, bbox):
    xmin, ymin, xmax, ymax = bbox
    frame = camera.data.view_frame(scene=scene)
    left, right = min(v.x for v in frame), max(v.x for v in frame)
    bottom, top, z = min(v.y for v in frame), max(v.y for v in frame), frame[0].z
    origin = camera.matrix_world.translation.copy()
    rotation = camera.matrix_world.to_3x3()
    inverse = target.matrix_world.inverted()
    local_origin = inverse @ origin
    local_rotation = inverse.to_3x3()
    eligible = visible = unoccluded = in_frame = 0
    for row in range(VISIBILITY_GRID):
        v = ymin + (ymax - ymin) * (row + .5) / VISIBILITY_GRID
        for column in range(VISIBILITY_GRID):
            u = xmin + (xmax - xmin) * (column + .5) / VISIBILITY_GRID
            direction = (rotation @ Vector((left + u * (right - left), bottom + v * (top - bottom), z))).normalized()
            local_direction = (local_rotation @ direction).normalized()
            target_hit = target.ray_cast(local_origin, local_direction)
            if not target_hit[0]:
                continue
            eligible += 1
            inside = 0 <= u <= 1 and 0 <= v <= 1
            in_frame += int(inside)
            hit = scene.ray_cast(depsgraph, origin, direction, distance=camera.data.clip_end)
            hit_target = hit[0] and hit[4].original == target.original
            unoccluded += int(hit_target)
            visible += int(inside and hit_target)
    return {"visible_fraction": visible / eligible if eligible else 0.0,
        "unoccluded_fraction": unoccluded / eligible if eligible else 0.0,
        "in_frame_fraction": in_frame / eligible if eligible else 0.0,
        "visibility_samples": eligible, "visibility_grid": VISIBILITY_GRID}


def _collisions(camera, objects):
    position = camera.matrix_world.translation
    clearance = camera.data.clip_start
    hits = []
    for object_id, obj in objects.items():
        p = obj.matrix_world.inverted() @ position
        scale = obj.matrix_world.to_scale()
        margin = clearance / max(min(abs(value) for value in scale), 1e-12)
        primitive = obj["previs_primitive"]
        if primitive == "mesh":
            nearest = obj.closest_point_on_mesh(p)
            inside = bool(nearest[0]) and (obj.matrix_world @ nearest[1] - position).length <= clearance
            if not inside and obj.data.get("previs_closed", False) and max(abs(value) for value in p) <= .5 + margin:
                # Odd/even crossings work for concave closed set pieces too. This
                # deliberately does not treat a thin sheet's whole bbox as solid.
                ray = Vector((.913, .327, .241)).normalized()
                origin = p.copy()
                crossings = 0
                for _ in range(len(obj.data.polygons) + 1):
                    hit = obj.ray_cast(origin, ray)
                    if not hit[0]:
                        break
                    crossings += 1
                    origin = hit[1] + ray * 1e-5
                inside = crossings % 2 == 1
        elif primitive == "sphere":
            inside = p.length <= .5 + margin
        elif primitive == "cylinder":
            inside = p.x * p.x + p.y * p.y <= (.5 + margin) ** 2 and abs(p.z) <= .5 + margin
        else:
            # The declared thin plane volume also participates in camera clearance.
            inside = max(abs(value) for value in p) <= .5 + margin
        if inside:
            hits.append(object_id)
    return hits


def _state(scene, shot: dict, objects: dict, frame: float):
    depsgraph = _frame(scene, frame)
    camera = scene.camera.evaluated_get(depsgraph)
    evaluated = {name: obj.evaluated_get(depsgraph) for name, obj in objects.items()}
    target = evaluated[shot["framing"]["object"]]
    bbox, depths = _projection(scene, camera, target)
    collision_objects = _collisions(camera, evaluated)
    result = {"frame": frame, "global_frame": shot["start"] + frame,
        "camera_position": list(camera.matrix_world.translation),
        "camera_quaternion": list(camera.matrix_world.to_quaternion().normalized()),
        "camera_matrix": [list(row) for row in camera.matrix_world],
        "lens_mm": float(camera.data.lens), "sensor_width_mm": float(camera.data.sensor_width),
        "bbox": bbox, "depth_range": [min(depths), max(depths)],
        "camera_collision": bool(collision_objects), "collision_objects": collision_objects,
        "objects": {name: {"location": list(obj.matrix_world.translation),
            "quaternion": list(obj.matrix_world.to_quaternion().normalized()), "scale": list(obj.matrix_world.to_scale()),
            "matrix_world": [list(row) for row in obj.matrix_world]} for name, obj in evaluated.items()}}
    result.update(_visibility(scene, camera, target, depsgraph, bbox))
    _finite(result, f"readback.{shot['id']}@{frame}")
    if min(result["objects"][name]["scale"][axis] for name in evaluated for axis in range(3)) <= 0:
        raise WorkerError("Saved animation has a nonpositive scale")
    return result


def _error(actual, expected, key="") -> float:
    if isinstance(expected, dict):
        return max((_error(actual[name], value, name) for name, value in expected.items()), default=0.0)
    if isinstance(expected, (list, tuple)):
        if len(actual) != len(expected):
            return math.inf
        if "quaternion" in key:
            return min(max(abs(a - b) for a, b in zip(actual, expected)), max(abs(a + b) for a, b in zip(actual, expected)))
        return max((_error(a, b, key) for a, b in zip(actual, expected)), default=0.0)
    if isinstance(expected, (int, float)):
        return abs(actual - expected)
    return 0.0 if actual == expected else math.inf


def _issues(shot: dict, sample: dict, clip_start: float, clip_end: float):
    framing = shot["framing"]
    bbox = sample["bbox"]
    height, margin = bbox[3] - bbox[1], framing["safe_margin"]
    result = []

    def add(code, detail):
        result.append({"shot": shot["id"], "frame": sample["frame"], "code": code, "detail": detail})

    if height < framing["min_height"] - 1e-5 or height > framing["max_height"] + 1e-5:
        add("height_fraction", {"actual": height, "min": framing["min_height"], "max": framing["max_height"]})
    if framing["require_full"] and (bbox[0] < margin - 1e-5 or bbox[1] < margin - 1e-5 or bbox[2] > 1 - margin + 1e-5 or bbox[3] > 1 - margin + 1e-5):
        add("unsafe_crop", {"bbox": bbox, "safe_margin": margin})
    if sample["depth_range"][0] <= clip_start:
        add("near_plane_or_behind_camera", {"minimum_depth": sample["depth_range"][0], "clip_start": clip_start})
    if sample["depth_range"][1] >= clip_end:
        add("far_plane_clipped", {"maximum_depth": sample["depth_range"][1], "clip_end": clip_end})
    if sample["visible_fraction"] + 1e-6 < framing["min_visible_fraction"]:
        add("visibility", {"actual": sample["visible_fraction"], "minimum": framing["min_visible_fraction"]})
    if sample["visibility_samples"] == 0:
        add("visibility_unsampled", "No isolated target silhouette ray hit")
    if sample["camera_collision"]:
        add("camera_collision", {"objects": sample["collision_objects"]})
    return result


def _render(core, lane: Path, scene, frame: int, relative: str):
    path = _out(core, lane, relative)
    if path.exists():
        raise WorkerError(f"Render target already exists: {relative}")
    _frame(scene, frame)
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True, scene=scene.name)
    if not path.is_file() or path.stat().st_size < 32:
        raise WorkerError(f"Missing or empty render: {relative}")
    header = path.read_bytes()[:24]
    if header[:8] != b"\x89PNG\r\n\x1a\n":
        raise WorkerError(f"Render is not a PNG: {relative}")
    size = [int.from_bytes(header[16:20], "big"), int.from_bytes(header[20:24], "big")]
    if size != [scene.render.resolution_x, scene.render.resolution_y]:
        raise WorkerError(f"Render dimensions mismatch: {relative}")
    return {"path": relative, "sha256": core.sha256_file(path), "bytes": path.stat().st_size, "resolution": size}


def _hold_issues(contract: dict, reports: list[dict]):
    stable = []
    for shot in reports:
        for sample in shot["samples"]:
            if shot["start"] + sample["frame"] >= contract["hold_start"]:
                # Names may differ between layouts. The interval must be one final shot.
                stable.append((shot["id"], sample))
    if not stable:
        raise WorkerError("No samples in the final stable interval")
    first_id, first = stable[0]
    fields = ("camera_position", "camera_quaternion", "lens_mm", "objects")
    expected = {key: first[key] for key in fields}
    result = []
    for shot_id, sample in stable[1:]:
        if shot_id != first_id or _error(sample, expected) > TRANSFORM_TOLERANCE:
            result.append({"shot": shot_id, "frame": sample["frame"], "code": "final_hold_moved", "detail": "Evaluated camera, lens, or object state changed during the final hold"})
    return result


def _build(core, job: dict, lane: Path, contract: dict, layout_only: bool = False):
    report_name = "layout-report.json" if layout_only else "backend-report.json"
    blend_name = "layout-preview.blend" if layout_only else "scene.blend"
    for target in (report_name, blend_name, "layouts", "shots"):
        if core.safe_path(lane, target, must_exist=False).exists():
            raise WorkerError(f"Build output already exists: {target}; prepare a new lane")
    source_file = bpy.data.filepath
    bpy.ops.wm.read_factory_settings(use_empty=True)
    # Factory defaults are intentionally discarded only inside this fresh background process.
    factory_scenes = list(bpy.data.scenes)
    bpy.context.preferences.filepaths.save_version = 0
    temp = _out(core, lane, "tmp/.directory")
    bpy.context.preferences.filepaths.temporary_directory = str(temp.parent)
    contract = dict(contract, _digest=job["contract_sha256"])
    report = {"schema": "product-tvc-layout/v1" if layout_only else REPORT_SCHEMA, "contract_sha256": job["contract_sha256"],
        "fixture": contract["fixture"], "blender_version": bpy.app.version_string,
        "engine": "BLENDER_WORKBENCH", "worker_pid": os.getpid(), "argv": sys.argv,
        "lane_root": str(lane), "blend_path": str(_out(core, lane, blend_name)),
        "opened_before_factory_reset": source_file,
        "worker_sha256": core.sha256_file(Path(__file__).resolve()),
        "core_sha256": core.sha256_file(Path(__file__).resolve().with_name("core.py")),
        "scene_json_sha256": core.sha256_file(lane / "scene.json"),
        "shots": [], "layouts": [], "issues": [], "artifacts": [],
        "orientation_policy": "world_up_projection_with_pole_transport_sign_continuity_and_explicit_roll",
        "limitations": LIMITATIONS, "visual_review": "required", "sampling_step_frames": SAMPLE_STEP}
    mesh_sets = {}
    layout_specs = {layout["id"]: layout for layout in contract["layouts"]}
    for layout in contract["layouts"]:
        scene = _new_scene(f"LAYOUT__{layout['id']}", contract, 1)
        scene["previs_layout_id"] = layout["id"]
        specs = {item["id"]: item for item in layout["objects"]}
        mesh_sets[layout["id"]] = {name: _mesh(spec, f"MESH__{layout['id']}__{name}") for name, spec in specs.items()}
        objects = {name: _object(scene, spec, mesh_sets[layout["id"]][name], layout["id"]) for name, spec in specs.items()}
        extent = max(max(spec["dimensions"]) for spec in layout["objects"])
        camera = _camera(scene, layout["camera"], extent)
        resolved, fits = _resolve_camera(scene, camera, layout["camera"], objects, specs, {}, core)
        key = resolved[0]
        camera.location = key["position"]
        camera.rotation_quaternion, _ = _orientation(key["position"], key["target"], key["roll_deg"])
        _camera_number(camera.data, "lens", key["lens_mm"])
        artifact = _render(core, lane, scene, 0, f"layouts/{layout['id']}.png")
        report["artifacts"].append(artifact)
        report["layouts"].append({"id": layout["id"], "scene": scene.name, "image_path": str(lane / artifact["path"]),
            "image_sha256": artifact["sha256"], "sha256": artifact["sha256"], "source_image_asset": layout["image_asset"], "fit_evidence": fits,
            "camera_position": list(camera.location), "camera_quaternion": list(camera.rotation_quaternion),
            "lens_mm": float(camera.data.lens), "layout_image_comparison": "required"})
        _log(core, lane, f"layout {layout['id']} rendered")
    if layout_only:
        # Layout calibration is a real stop: no shot scene or animation exists.
        first = bpy.data.scenes[report["layouts"][0]["scene"]]
        _frame(first, 0)
        for scene in factory_scenes:
            bpy.data.scenes.remove(scene)
        bpy.ops.wm.save_as_mainfile(filepath=report["blend_path"], check_existing=False)
        blend = Path(report["blend_path"])
        if not blend.is_file() or blend.stat().st_size == 0:
            raise WorkerError("Blender did not save layout-preview.blend")
        report["blend_sha256"] = core.sha256_file(blend)
        report["artifacts"].append({"path": blend_name, "sha256": report["blend_sha256"], "bytes": blend.stat().st_size})
        report["completed_at"] = time.time()
        report["technical_status"] = "layout_renders_ready_comparison_required"
        _write(core, lane, report_name, report)
        _log(core, lane, "layout-only complete; no shot animation was constructed")
        return {"ok": True, "mode": "layout", "report": str(lane / report_name), "worker_pid": os.getpid(),
                "issue_count": 0, "blend_sha256": report["blend_sha256"]}
    for shot in contract["shots"]:
        frames = shot["end"] - shot["start"]
        layout = layout_specs[shot["layout"]]
        scene = _new_scene(f"SHOT__{shot['id']}", contract, frames)
        scene["previs_shot_id"], scene["previs_layout_id"] = shot["id"], layout["id"]
        scene["previs_global_start"] = shot["start"]
        objects = {spec["id"]: _object(scene, spec, mesh_sets[layout["id"]][spec["id"]], layout["id"]) for spec in layout["objects"]}
        extent = max(max(spec["dimensions"]) for spec in layout["objects"])
        camera = _camera(scene, shot["camera"], extent)
        expected, fits = _bake(scene, shot, layout, objects, camera, core)
        shot_report = {"id": shot["id"], "layout": shot["layout"], "scene": scene.name, "start": shot["start"], "end": shot["end"],
            "frames": frames, "directory": str(lane / "shots" / shot["id"]), "samples": [], "issues": [],
            "fit_evidence": fits, "rendered_frames": [], "resolved_camera_keys": json.loads(scene["previs_camera_keys"]),
            "bake": _check_linear([camera, camera.data, *objects.values()]), "maximum_oracle_error": 0.0}
        for frame, oracle in zip(_times(frames), expected):
            sample = _state(scene, shot, objects, frame)
            error = _error(sample, oracle)
            if error > TRANSFORM_TOLERANCE:
                raise WorkerError(f"Baked readback differs from analytic half-frame state in {shot['id']} at {frame}: {error}")
            shot_report["maximum_oracle_error"] = max(error, shot_report["maximum_oracle_error"])
            shot_report["samples"].append(sample)
            shot_report["issues"].extend(_issues(shot, sample, camera.data.clip_start, camera.data.clip_end))
            if frame.is_integer():
                artifact = _render(core, lane, scene, int(frame), f"shots/{shot['id']}/{int(frame) + 1:06d}.png")
                report["artifacts"].append(artifact)
                shot_report["rendered_frames"].append(artifact)
        report["shots"].append(shot_report)
        report["issues"].extend(shot_report["issues"])
        _frame(scene, 0)
        _log(core, lane, f"shot {shot['id']} rendered {frames} frames; sampled {len(expected)} states; issues={len(shot_report['issues'])}")
    report["issues"].extend(_hold_issues(contract, report["shots"]))
    # Leave the saved file at the first shot, preserving every independent scene.
    first = bpy.data.scenes[report["shots"][0]["scene"]]
    _frame(first, 0)
    for scene in factory_scenes:
        bpy.data.scenes.remove(scene)
    bpy.ops.wm.save_as_mainfile(filepath=report["blend_path"], check_existing=False)
    blend = Path(report["blend_path"])
    if not blend.is_file() or blend.stat().st_size == 0:
        raise WorkerError("Blender did not save the lane's scene.blend")
    report["blend_sha256"] = core.sha256_file(blend)
    report["artifacts"].append({"path": "scene.blend", "sha256": report["blend_sha256"], "bytes": blend.stat().st_size})
    report["geometry_sharing"] = {layout_id: {name: {"mesh": mesh.name, "users": mesh.users} for name, mesh in meshes.items()} for layout_id, meshes in mesh_sets.items()}
    report["completed_at"] = time.time()
    report["technical_status"] = "issues_found" if report["issues"] else "checks_passed_visual_review_required"
    _write(core, lane, "backend-report.json", report)
    _log(core, lane, f"build complete; issue_count={len(report['issues'])}")
    return {"ok": True, "mode": "build", "report": str(lane / "backend-report.json"), "worker_pid": os.getpid(),
            "issue_count": len(report["issues"]), "blend_sha256": report["blend_sha256"]}


def _inspect(core, job: dict, lane: Path, contract: dict):
    report_path = core.safe_path(lane, "backend-report.json", must_exist=True)
    report = _read_json(report_path)
    if report.get("schema") != REPORT_SCHEMA or report.get("contract_sha256") != job["contract_sha256"]:
        raise WorkerError("Build report is not bound to this contract")
    if report.get("worker_pid") == os.getpid():
        raise WorkerError("Cold reopen requires a fresh Blender process")
    if report.get("worker_sha256") != core.sha256_file(Path(__file__).resolve()) or report.get("core_sha256") != core.sha256_file(Path(__file__).resolve().with_name("core.py")):
        raise WorkerError("Build and inspect must use the same package code version")
    blend = core.safe_path(lane, "scene.blend", must_exist=True)
    if not bpy.data.filepath or Path(bpy.data.filepath).resolve() != blend:
        raise WorkerError("Inspect must start by cold-opening this lane's scene.blend")
    before_hash = core.sha256_file(blend)
    if before_hash != report.get("blend_sha256"):
        raise WorkerError("scene.blend changed after the build report")
    for artifact in report["artifacts"]:
        path = core.safe_path(lane, artifact["path"], must_exist=True)
        if core.sha256_file(path) != artifact["sha256"]:
            raise WorkerError(f"Artifact changed or is incomplete: {artifact['path']}")
    expected_ids = [shot["id"] for shot in contract["shots"]]
    if [shot["id"] for shot in report["shots"]] != expected_ids:
        raise WorkerError("Build report does not cover the contract's exact shot order")
    result = {"schema": "product-tvc-reopen/v1", "contract_sha256": job["contract_sha256"],
        "build_worker_pid": report["worker_pid"], "worker_pid": os.getpid(), "argv": sys.argv,
        "blend_path": str(blend), "blend_sha256": before_hash, "backend_report_sha256": core.sha256_file(report_path),
        "blender_version": bpy.app.version_string, "sampling_step_frames": SAMPLE_STEP, "shots": [], "issues": [],
        "artifacts_verified": len(report["artifacts"]), "maximum_error": 0.0, "limitations": LIMITATIONS}
    for shot, built in zip(contract["shots"], report["shots"]):
        scene = bpy.data.scenes.get(built["scene"])
        if scene is None or scene.get("previs_contract_sha256") != job["contract_sha256"] or scene.get("previs_shot_id") != shot["id"]:
            raise WorkerError(f"Missing/mismatched saved scene for {shot['id']}")
        objects = {obj["previs_object_id"]: obj for obj in scene.objects if "previs_object_id" in obj}
        expected_objects = {obj["id"] for layout in contract["layouts"] if layout["id"] == shot["layout"] for obj in layout["objects"]}
        if set(objects) != expected_objects:
            raise WorkerError(f"Saved objects do not match layout in {shot['id']}")
        frames = shot["end"] - shot["start"]
        if [sample["frame"] for sample in built["samples"]] != _times(frames):
            raise WorkerError("Build report has missing or duplicate samples")
        linear = _check_linear([scene.camera, scene.camera.data, *objects.values()])
        samples, maximum = [], 0.0
        for expected in built["samples"]:
            actual = _state(scene, shot, objects, expected["frame"])
            error = _error(actual, expected)
            maximum = max(maximum, error)
            if error > TRANSFORM_TOLERANCE:
                raise WorkerError(f"Cold readback differs in {shot['id']} at {expected['frame']}: {error}")
            samples.append(actual)
        result["shots"].append({"id": shot["id"], "samples": samples, "maximum_error": maximum, "bake": linear})
        result["maximum_error"] = max(maximum, result["maximum_error"])
        _log(core, lane, f"cold readback {shot['id']}; samples={len(samples)} max_error={maximum:.8g}")
    after_hash = core.sha256_file(blend)
    if before_hash != after_hash:
        raise WorkerError("Cold inspection modified the saved blend")
    result["blend_unchanged"] = True
    result["status"] = "readback_matches_build"
    result["completed_at"] = time.time()
    _write(core, lane, "reopen.json", result)
    return {"ok": True, "mode": "inspect", "report": str(lane / "reopen.json"), "worker_pid": os.getpid(),
            "maximum_error": result["maximum_error"], "issue_count": 0}


def run(job_path: str | Path) -> dict:
    """Execute one validated build or cold inspect; return a compact result.

    The JSON reports contain the full per-frame evidence. Framing violations are
    reported as issues, making artifacts available for correction; malformed jobs,
    unsafe paths, missing output, and readback mismatches raise WorkerError.
    """
    core, job, lane, contract = _job(job_path)
    _blender()
    _claim(core, lane, job)
    _log(core, lane, f"{job['mode']} started; contract={job['contract_sha256']}")
    if job["mode"] == "inspect":
        return _inspect(core, job, lane, contract)
    return _build(core, job, lane, contract, layout_only=job["mode"] == "layout")


def main() -> int:
    arguments = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    if len(arguments) != 1:
        print("Expected exactly one absolute job_path after --", file=sys.stderr)
        return 2
    core = lane = job = None
    try:
        core, job, lane, _ = _job(arguments[0])
        result = run(arguments[0])
        _write(core, lane, "worker-result.json", result)
        print(json.dumps(result, ensure_ascii=False), flush=True)
        return 0
    except Exception as exc:
        result = {"ok": False, "worker_pid": os.getpid(), "error": str(exc), "traceback": traceback.format_exc()}
        if job is not None:
            result["mode"] = job["mode"]
        if core is not None and lane is not None:
            marker = core.safe_path(lane, f"execution/{job['mode']}-started.json", must_exist=False)
            # A duplicate invocation must not overwrite the active owner's result.
            if not marker.exists() or _read_json(marker).get("worker_pid") == os.getpid():
                _write(core, lane, "worker-result.json", result)
                _log(core, lane, f"FAILED: {type(exc).__name__}: {exc}")
        print(json.dumps(result, ensure_ascii=False), file=sys.stderr, flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
