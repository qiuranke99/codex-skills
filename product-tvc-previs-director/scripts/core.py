"""Portable scene contracts, continuous motion, and synthetic development input.

No Blender or third-party imports are used here.  Rotation channels are ordinary
degrees: there is no implicit angle wrapping.  Author intermediate keys for full
turns.  Hermite is C1 across nonuniform key times; segment mode instead applies
the LEFT key's ease.  Endpoints continue at a one-sided velocity by default;
endpoint_mode='stop' explicitly brakes to zero. States omit frame/ease metadata.
"""

from __future__ import annotations

import bisect
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import re
import struct
import tempfile
from typing import Any
import zlib


SCHEMA = "product-tvc-previs/v1"
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}\Z")
_HASH = re.compile(r"[0-9a-fA-F]{64}\Z")
_MODES = {"hermite", "segment"}
_EASES = {"linear", "smoothstep", "smootherstep"}
_ENDPOINTS = {"continue", "stop"}
_RESERVED = {"CON", "PRN", "AUX", "NUL"} | {
    f"{prefix}{number}" for prefix in ("COM", "LPT") for number in range(1, 10)
}


class ContractError(ValueError):
    """Invalid, ambiguous, unsafe, or unverifiable contract input."""


def _fail(where: str, message: str) -> None:
    raise ContractError(f"{where}: {message}")


def _mapping(value: Any, where: str, required: set[str], optional: set[str] | None = None) -> dict:
    if not isinstance(value, dict):
        _fail(where, "expected an object")
    missing = required - value.keys()
    if missing:
        _fail(where, "missing fields: " + ", ".join(sorted(missing)))
    extra = value.keys() - required - (optional or set())
    if extra:
        _fail(where, "unknown fields: " + ", ".join(sorted(map(str, extra))))
    return value


def _list(value: Any, where: str, minimum: int = 0) -> list:
    if not isinstance(value, list) or len(value) < minimum:
        _fail(where, f"expected a list with at least {minimum} item(s)")
    return value


def _text(value: Any, where: str, *, empty: bool = False) -> str:
    if not isinstance(value, str) or (not empty and not value.strip()):
        _fail(where, "expected nonempty text" if not empty else "expected text")
    if "\x00" in value:
        _fail(where, "NUL is not permitted")
    return value


def _identifier(value: Any, where: str) -> str:
    if not isinstance(value, str) or not _ID.fullmatch(value):
        _fail(where, "expected a 1-64 character identifier using letters, digits, '_' or '-'")
    if value.upper() in _RESERVED:
        _fail(where, "reserved filesystem identifier")
    return value


def _number(value: Any, where: str, *, low: float | None = None,
            high: float | None = None, positive: bool = False, integer: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        _fail(where, "expected an integer" if integer else "expected a finite number (not boolean)")
    if integer and not isinstance(value, int):
        _fail(where, "expected an integer")
    try:
        finite = math.isfinite(value)
    except (OverflowError, TypeError):
        finite = False
    if not finite:
        _fail(where, "expected a finite number")
    if positive and value <= 0:
        _fail(where, "must be greater than zero")
    if low is not None and value < low:
        _fail(where, f"must be at least {low}")
    if high is not None and value > high:
        _fail(where, f"must be at most {high}")
    return value


def _boolean(value: Any, where: str) -> bool:
    if type(value) is not bool:
        _fail(where, "expected a boolean")
    return value


def _vector(value: Any, where: str, *, length: int = 3, positive: bool = False,
            low: float | None = None, high: float | None = None) -> list:
    if not isinstance(value, list) or len(value) != length:
        _fail(where, f"expected a {length}-number list")
    for i, component in enumerate(value):
        _number(component, f"{where}[{i}]", positive=positive, low=low, high=high)
    return value


def _choice(value: Any, choices: set[str], where: str) -> str:
    if not isinstance(value, str) or value not in choices:
        _fail(where, "expected one of: " + ", ".join(sorted(choices)))
    return value


def _relative_parts(relative: Any) -> list[str]:
    _text(relative, "path")
    # Apply Windows portability rules on every OS, including drive-relative
    # paths, alternate data streams, UNC paths, device names, and trailing dots.
    if relative.startswith(("/", "\\")) or any(char in relative for char in ':<>"|?*'):
        _fail("path", "absolute, drive, UNC, ADS, or reserved paths are not permitted")
    parts = relative.replace("\\", "/").split("/")
    for part in parts:
        if not part or part in {".", ".."}:
            _fail("path", "empty or dot path components are not permitted")
        if part.endswith((".", " ")) or any(ord(char) < 32 for char in part):
            _fail("path", "unsafe path component")
        if part.split(".", 1)[0].upper() in _RESERVED:
            _fail("path", "reserved device path is not permitted")
    return parts


def safe_path(root: str | Path, relative: str, must_exist: bool = False) -> Path:
    """Resolve an asset/lane-relative path without traversal or symlink escape."""
    parts = _relative_parts(relative)
    try:
        anchor = Path(root).resolve(strict=True)
        if not anchor.is_dir():
            _fail("root", "expected an existing directory")
        resolved = anchor.joinpath(*parts).resolve(strict=must_exist)
        if not resolved.is_relative_to(anchor):
            _fail("path", "resolved path escapes root (including symlinks)")
        if must_exist and not resolved.exists():
            _fail("path", "required path does not exist")
        return resolved
    except ContractError:
        raise
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        raise ContractError(f"path: cannot resolve {relative!r}: {exc}") from exc


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    try:
        with Path(path).open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except (OSError, TypeError, ValueError) as exc:
        raise ContractError(f"asset: cannot read {path}: {exc}") from exc
    return digest.hexdigest()


def _json_bytes(data: Any) -> bytes:
    try:
        return json.dumps(data, ensure_ascii=False, allow_nan=False, sort_keys=True,
                          separators=(",", ":")).encode("utf-8")
    except (TypeError, ValueError, OverflowError) as exc:
        raise ContractError(f"JSON: input is not finite serializable JSON: {exc}") from exc


def contract_digest(data: dict) -> str:
    return hashlib.sha256(_json_bytes(data)).hexdigest()


def dump_json(path: str | Path, data: Any) -> None:
    """Atomically write UTF-8 JSON; callers own authorization of the output path."""
    _json_bytes(data)
    target = Path(path)
    temporary = None
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n",
                                         prefix=f".{target.name}.", suffix=".tmp",
                                         dir=target.parent, delete=False) as handle:
            temporary = Path(handle.name)
            json.dump(data, handle, ensure_ascii=False, allow_nan=False, indent=2)
            handle.write("\n")
        os.replace(temporary, target)
    except (OSError, TypeError, ValueError) as exc:
        raise ContractError(f"JSON: cannot write {target}: {exc}") from exc
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def _pairs_unique(pairs: list[tuple[str, Any]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            _fail("JSON", f"duplicate field {key!r}")
        result[key] = value
    return result


def load_contract(path: str | Path, verify_assets: bool = True) -> dict:
    source = Path(path)
    try:
        data = json.loads(source.read_text(encoding="utf-8-sig"), object_pairs_hook=_pairs_unique,
                          parse_constant=lambda value: _fail("JSON", f"nonfinite number {value}"))
    except ContractError:
        raise
    except (OSError, UnicodeError, ValueError, TypeError, RecursionError) as exc:
        raise ContractError(f"contract: cannot load {source}: {exc}") from exc
    validate_contract(data, source.parent, verify_assets=verify_assets)
    return data


def ease_value(name: str, t: float) -> float:
    _choice(name, _EASES, "ease")
    _number(t, "ease.t", low=0, high=1)
    if name == "linear":
        return float(t)
    if name == "smoothstep":
        return t * t * (3 - 2 * t)
    return t * t * t * (t * (6 * t - 15) + 10)


def _state(value: Any) -> Any:
    if isinstance(value, dict):
        return {name: _state(item) for name, item in value.items() if name not in {"frame", "ease"}}
    if isinstance(value, list):
        return [_state(item) for item in value]
    return copy.deepcopy(value)


def _tangent(values: list[float], frames: list[float], index: int, endpoint_mode: str) -> float:
    if index == 0 or index == len(values) - 1:
        if endpoint_mode == "stop":
            return 0.0
        a, b = (0, 1) if index == 0 else (len(values) - 2, len(values) - 1)
        return (values[b] - values[a]) / (frames[b] - frames[a])
    previous, current, following = values[index - 1:index + 2]
    if previous == current or current == following:
        return 0.0
    before, after = frames[index] - frames[index - 1], frames[index + 1] - frames[index]
    # Weighted central difference is valid for nonuniform key times.
    slope_before = (current - previous) / before
    slope_after = (following - current) / after
    return (after * slope_before + before * slope_after) / (before + after)


def _interpolate_values(values: list[Any], frames: list[float], left: int,
                        t: float, mode: str, endpoint_mode: str, where: str = "keys") -> Any:
    start, finish = values[left], values[left + 1]
    if isinstance(start, dict):
        fields = set(start) - {"frame", "ease"}
        if any(not isinstance(item, dict) or set(item) - {"frame", "ease"} != fields for item in values):
            _fail(where, "interpolation requires matching fields; resolve fit keys to position first")
        return {name: _interpolate_values([item[name] for item in values], frames, left, t,
                                         mode, endpoint_mode, f"{where}.{name}") for name in start if name in fields}
    if isinstance(start, list):
        if any(not isinstance(item, list) or len(item) != len(start) for item in values):
            _fail(where, "interpolation requires equal-length lists")
        return [_interpolate_values([item[i] for item in values], frames, left, t,
                                    mode, endpoint_mode, f"{where}[{i}]") for i in range(len(start))]
    if isinstance(start, (int, float)) and not isinstance(start, bool):
        for value in values:
            _number(value, where)
        if start == finish:
            return copy.deepcopy(start)
        if mode == "segment":
            result = start + (finish - start) * t
        else:
            span = frames[left + 1] - frames[left]
            m0 = _tangent(values, frames, left, endpoint_mode)
            m1 = _tangent(values, frames, left + 1, endpoint_mode)
            t2, t3 = t * t, t * t * t
            result = ((2 * t3 - 3 * t2 + 1) * start + (t3 - 2 * t2 + t) * span * m0
                      + (-2 * t3 + 3 * t2) * finish + (t3 - t2) * span * m1)
        _number(result, where)
        return result
    if any(type(item) is not type(start) or item != start for item in values):
        _fail(where, "nonnumeric interpolation fields must be identical")
    return copy.deepcopy(start)


def interpolate_keys(keys: list[dict], frame: float, mode: str = "hermite",
                     endpoint_mode: str = "continue") -> dict:
    """Evaluate a state, clamping outside the keys; no implicit angle wrap.

    Hermite continues with one-sided endpoint tangents unless endpoint_mode is
    'stop'. A scalar channel adjacent to an equal value has a zero tangent at
    that key, making repeated-state holds exact. Other interior tangents use
    weighted nonuniform central differences.
    Fit keys should be geometrically resolved by the backend before evaluation.
    """
    _choice(mode, _MODES, "interpolation")
    _choice(endpoint_mode, _ENDPOINTS, "endpoint_mode")
    _number(frame, "frame")
    _list(keys, "keys", 1)
    frames = []
    for index, key in enumerate(keys):
        if not isinstance(key, dict) or "frame" not in key:
            _fail(f"keys[{index}]", "expected an object with a frame")
        value = _number(key["frame"], f"keys[{index}].frame")
        if frames and value <= frames[-1]:
            _fail("keys", "frames must be strictly increasing")
        _choice(key.get("ease", "linear"), _EASES, f"keys[{index}].ease")
        frames.append(value)
    if frame <= frames[0] or len(keys) == 1:
        return _state(keys[0])
    if frame >= frames[-1]:
        return _state(keys[-1])
    left = bisect.bisect_right(frames, frame) - 1
    t = (frame - frames[left]) / (frames[left + 1] - frames[left])
    if mode == "segment":
        t = ease_value(keys[left].get("ease", "linear"), t)
    return _interpolate_values(keys, frames, left, t, mode, endpoint_mode)


def _key_times(keys: Any, frames: int, where: str) -> list[dict]:
    _list(keys, where, 1 if frames == 1 else 2)
    previous = -1
    for index, key in enumerate(keys):
        if not isinstance(key, dict) or "frame" not in key:
            _fail(f"{where}[{index}]", "expected an object containing frame")
        value = _number(key["frame"], f"{where}[{index}].frame", integer=True, low=0, high=frames - 1)
        if value <= previous:
            _fail(where, "frames must be strictly increasing without duplicates")
        previous = value
    if keys[0]["frame"] != 0 or keys[-1]["frame"] != frames - 1:
        _fail(where, f"keys must cover local frame 0 through {frames - 1}")
    return keys


def _validate_camera(camera: Any, frames: int, objects: set[str], where: str) -> None:
    _mapping(camera, where, {"sensor_width_mm", "keys"}, {"interpolation", "endpoint_mode"})
    _number(camera["sensor_width_mm"], where + ".sensor_width_mm", positive=True)
    _choice(camera.get("interpolation", "hermite"), _MODES, where + ".interpolation")
    _choice(camera.get("endpoint_mode", "continue"), _ENDPOINTS, where + ".endpoint_mode")
    keys = _key_times(camera["keys"], frames, where + ".keys")
    if frames == 1 and len(keys) != 1:
        _fail(where, "a layout camera must have exactly one key at frame 0")
    for index, key in enumerate(keys):
        here = f"{where}.keys[{index}]"
        _mapping(key, here, {"frame", "target", "lens_mm", "roll_deg", "ease"}, {"position", "fit"})
        if ("position" in key) == ("fit" in key):
            _fail(here, "provide exactly one of position or fit")
        _vector(key["target"], here + ".target")
        _number(key["lens_mm"], here + ".lens_mm", positive=True)
        _number(key["roll_deg"], here + ".roll_deg")
        _choice(key["ease"], _EASES, here + ".ease")
        if "position" in key:
            _vector(key["position"], here + ".position")
            if key["position"] == key["target"]:
                _fail(here, "camera position and target must differ")
        else:
            fit = _mapping(key["fit"], here + ".fit",
                           {"object", "height_fraction", "azimuth_deg", "elevation_deg", "target_offset"})
            if not isinstance(fit["object"], str) or fit["object"] not in objects:
                _fail(here + ".fit.object", "unknown object in the current layout")
            _number(fit["height_fraction"], here + ".fit.height_fraction", positive=True)
            _number(fit["azimuth_deg"], here + ".fit.azimuth_deg")
            _number(fit["elevation_deg"], here + ".fit.elevation_deg", low=-90, high=90)
            _vector(fit["target_offset"], here + ".fit.target_offset")


def _constant_after(keys: list[dict], start: int, where: str) -> None:
    index = bisect.bisect_right([key["frame"] for key in keys], start) - 1
    expected = _state(keys[index])
    if any(_state(key) != expected for key in keys[index + 1:]):
        _fail(where, "motion continues inside the final stable hold; repeat the complete state before hold_start")


def _check_layout_image(path: Path, where: str) -> None:
    try:
        with path.open("rb") as handle:
            header = handle.read(4096)
    except OSError as exc:
        raise ContractError(f"{where}: cannot read layout image: {exc}") from exc
    known = (header.startswith(b"\x89PNG\r\n\x1a\n") or header.startswith(b"\xff\xd8\xff")
             or header.startswith((b"GIF87a", b"GIF89a", b"BM", b"II*\x00", b"MM\x00*"))
             or (header.startswith(b"RIFF") and header[8:12] == b"WEBP"))
    if not known:
        try:
            import xml.etree.ElementTree as element_tree
            if b"<!DOCTYPE" in header.upper() or b"<!ENTITY" in header.upper():
                _fail(where, "layout SVG must not use external entities or a document type")
            element = element_tree.parse(path).getroot()
            known = element.tag.rsplit("}", 1)[-1] == "svg"
        except (element_tree.ParseError, UnicodeError, OSError):
            known = False
    if not known:
        _fail(where, "expected an actual PNG, JPEG, GIF, BMP, TIFF, WebP, or SVG layout image")


def validate_contract(data: dict, root: str | Path | None = None,
                      verify_assets: bool = False) -> None:
    """Validate structure, references, assets, motion coverage, and true hold."""
    _mapping(data, "contract", {"schema", "id", "fixture", "fps", "duration_frames", "resolution",
                                 "hold_start", "assets", "creative", "layouts", "shots", "provider"})
    if data["schema"] != SCHEMA:
        _fail("schema", f"expected {SCHEMA}")
    _identifier(data["id"], "id")
    _boolean(data["fixture"], "fixture")
    fps = _number(data["fps"], "fps", integer=True, low=1, high=120)
    duration = _number(data["duration_frames"], "duration_frames", integer=True, positive=True)
    resolution = _vector(data["resolution"], "resolution", length=2, positive=True)
    for index, value in enumerate(resolution):
        _number(value, f"resolution[{index}]", integer=True, low=2)
        if value % 2:
            _fail("resolution", "width and height must be even integers")
    hold = _number(data["hold_start"], "hold_start", integer=True, low=0, high=duration - 1)
    if duration - hold < fps:
        _fail("hold_start", "final stable hold must last at least one second")
    _boolean(verify_assets, "verify_assets")
    if verify_assets and root is None:
        _fail("root", "asset verification requires the contract directory")

    assets = {}
    roles = set()
    for index, asset in enumerate(_list(data["assets"], "assets", 1)):
        here = f"assets[{index}]"
        _mapping(asset, here, {"id", "role", "path", "sha256"})
        asset_id = _identifier(asset["id"], here + ".id")
        if asset_id.upper().startswith("PREVIS-"):
            _fail(here + ".id", "PREVIS- is reserved for generated video attachments")
        if asset_id in assets:
            _fail(here, f"duplicate asset id {asset_id}")
        _choice(asset["role"], {"product", "look", "layout", "art"}, here + ".role")
        _relative_parts(asset["path"])
        if not isinstance(asset["sha256"], str) or not _HASH.fullmatch(asset["sha256"]):
            _fail(here + ".sha256", "expected 64 hexadecimal SHA256 characters")
        resolved = safe_path(root, asset["path"], must_exist=verify_assets) if root is not None else None
        if verify_assets:
            if not resolved.is_file():
                _fail(here + ".path", "asset must be a regular file")
            if sha256_file(resolved).lower() != asset["sha256"].lower():
                _fail(here + ".sha256", "asset hash mismatch; input changed")
            if asset["role"] == "layout":
                _check_layout_image(resolved, here + ".path")
        assets[asset_id] = asset
        roles.add(asset["role"])
    required_roles = {"layout"} if data["fixture"] else {"product", "look", "layout"}
    if not required_roles <= roles:
        _fail("assets", "missing required asset roles: " + ", ".join(sorted(required_roles - roles)))

    fields = {"concept", "product_facts", "unknowns", "look", "lighting", "material_process",
              "identity", "text_lock", "photography"}
    optional_creative = {"scene_design", "previs_rules", "visibility"}
    _mapping(data["creative"], "creative", fields, optional_creative)
    for field in fields:
        _text(data["creative"][field], "creative." + field, empty=field == "unknowns")
    for field in optional_creative & data["creative"].keys():
        _text(data["creative"][field], "creative." + field)

    layouts = {}
    for index, layout in enumerate(_list(data["layouts"], "layouts", 1)):
        here = f"layouts[{index}]"
        _mapping(layout, here, {"id", "image_asset", "rationale", "objects", "camera"})
        layout_id = _identifier(layout["id"], here + ".id")
        if layout_id.casefold() in {value.casefold() for value in layouts}:
            _fail(here, f"duplicate layout id including case-insensitive filesystem collision: {layout_id}")
        image_id = layout["image_asset"]
        if not isinstance(image_id, str) or image_id not in assets or assets[image_id]["role"] != "layout":
            _fail(here + ".image_asset", "must reference an existing layout image asset")
        _text(layout["rationale"], here + ".rationale")
        objects = {}
        for number, obj in enumerate(_list(layout["objects"], here + ".objects", 1)):
            at = f"{here}.objects[{number}]"
            _mapping(obj, at, {"id", "role", "primitive", "location", "dimensions", "rotation_deg", "color", "rationale"},
                     {"vertices", "faces"})
            object_id = _identifier(obj["id"], at + ".id")
            if object_id in objects:
                _fail(at, f"duplicate object id {object_id}")
            _choice(obj["role"], {"product", "set", "material"}, at + ".role")
            _choice(obj["primitive"], {"cube", "sphere", "cylinder", "plane", "mesh"}, at + ".primitive")
            _vector(obj["location"], at + ".location")
            _vector(obj["dimensions"], at + ".dimensions", positive=True)
            _vector(obj["rotation_deg"], at + ".rotation_deg")
            _vector(obj["color"], at + ".color", low=0, high=1)
            _text(obj["rationale"], at + ".rationale")
            if obj["primitive"] == "mesh":
                vertices = _list(obj.get("vertices"), at + ".vertices", 3)
                faces = _list(obj.get("faces"), at + ".faces", 1)
                if len(vertices) > 5000 or len(faces) > 10000:
                    _fail(at, "low-cost mesh limit is 5000 vertices and 10000 faces")
                for vertex_index, vertex in enumerate(vertices):
                    _vector(vertex, f"{at}.vertices[{vertex_index}]")
                extents = [max(v[axis] for v in vertices) - min(v[axis] for v in vertices) for axis in range(3)]
                for axis, extent in enumerate(extents):
                    _number(extent, f"{at}.vertices.extent[{axis}]")
                if sum(extent > 0 for extent in extents) < 2:
                    _fail(at + ".vertices", "mesh must span at least two axes; planar surfaces are permitted")
                largest = max(extents)
                normalized = [[(vertex[axis] - vertices[0][axis]) / largest for axis in range(3)] for vertex in vertices]
                for face_index, face in enumerate(faces):
                    _list(face, f"{at}.faces[{face_index}]", 3)
                    for corner, vertex_index in enumerate(face):
                        _number(vertex_index, f"{at}.faces[{face_index}][{corner}]", integer=True,
                                low=0, high=len(vertices) - 1)
                    if len(set(face)) != len(face):
                        _fail(f"{at}.faces[{face_index}]", "face vertex indices must be distinct")
                    points = [normalized[index] for index in face]
                    edges = [_vsub(point, points[0]) for point in points[1:]]
                    baseline = next((edge for edge in edges if any(component != 0 for component in edge)), [0, 0, 0])
                    if not any(any(component != 0 for component in _cross(baseline, edge)) for edge in edges):
                        _fail(f"{at}.faces[{face_index}]", "face is degenerate: all vertices are collinear")
            elif "vertices" in obj or "faces" in obj:
                _fail(at, "vertices/faces are only supported for primitive=mesh")
            objects[object_id] = obj
        if not any(obj["role"] == "product" for obj in objects.values()):
            _fail(here + ".objects", "at least one product proxy is required")
        _validate_camera(layout["camera"], 1, set(objects), here + ".camera")
        layouts[layout_id] = (layout, objects)

    shot_ids = set()
    cursor = 0
    shots = _list(data["shots"], "shots", 1)
    for index, shot in enumerate(shots):
        here = f"shots[{index}]"
        _mapping(shot, here, {"id", "layout", "start", "end", "purpose", "entry_state", "exit_state",
                               "transition", "camera", "animations", "framing", "narrative"})
        shot_id = _identifier(shot["id"], here + ".id")
        if shot_id.upper() == "FULL":
            _fail(here + ".id", "FULL is reserved for the full-video attachment")
        if shot_id.casefold() in {value.casefold() for value in shot_ids}:
            _fail(here, f"duplicate shot id including case-insensitive filesystem collision: {shot_id}")
        shot_ids.add(shot_id)
        if not isinstance(shot["layout"], str) or shot["layout"] not in layouts:
            _fail(here + ".layout", "unknown layout reference")
        objects = layouts[shot["layout"]][1]
        start = _number(shot["start"], here + ".start", integer=True, low=0, high=duration - 1)
        end = _number(shot["end"], here + ".end", integer=True, low=1, high=duration)
        if start != cursor:
            _fail(here + ".start", f"expected {cursor}; timeline must have no gap or overlap")
        if end <= start:
            _fail(here + ".end", "shot must have positive duration")
        cursor = end
        for field in ("purpose", "entry_state", "exit_state"):
            _text(shot[field], here + "." + field)
        transition = _mapping(shot["transition"], here + ".transition", {"kind", "relation", "description"})
        _choice(transition["kind"], {"hard_cut"}, here + ".transition.kind")
        _choice(transition["relation"], {"continuation", "association", "display_time"}, here + ".transition.relation")
        _text(transition["description"], here + ".transition.description")
        _validate_camera(shot["camera"], end - start, set(objects), here + ".camera")
        animated = set()
        for number, animation in enumerate(_list(shot["animations"], here + ".animations")):
            at = f"{here}.animations[{number}]"
            _mapping(animation, at, {"object", "keys"}, {"interpolation", "endpoint_mode"})
            object_id = animation["object"]
            if not isinstance(object_id, str) or object_id not in objects:
                _fail(at + ".object", "unknown object reference in this layout")
            if object_id in animated:
                _fail(at, "an object may have only one animation per shot")
            animated.add(object_id)
            _choice(animation.get("interpolation", "hermite"), _MODES, at + ".interpolation")
            _choice(animation.get("endpoint_mode", "continue"), _ENDPOINTS, at + ".endpoint_mode")
            for key_index, key in enumerate(_key_times(animation["keys"], end - start, at + ".keys")):
                point = f"{at}.keys[{key_index}]"
                _mapping(key, point, {"frame", "location", "rotation_deg", "scale", "ease"})
                _vector(key["location"], point + ".location")
                _vector(key["rotation_deg"], point + ".rotation_deg")
                _vector(key["scale"], point + ".scale", positive=True)
                _choice(key["ease"], _EASES, point + ".ease")
        framing = _mapping(shot["framing"], here + ".framing",
                           {"object", "min_height", "max_height", "safe_margin", "require_full", "min_visible_fraction"})
        if not isinstance(framing["object"], str) or framing["object"] not in objects:
            _fail(here + ".framing.object", "unknown framing object")
        low = _number(framing["min_height"], here + ".framing.min_height", low=0)
        high = _number(framing["max_height"], here + ".framing.max_height", positive=True)
        if high <= low:
            _fail(here + ".framing", "max_height must exceed min_height")
        margin = _number(framing["safe_margin"], here + ".framing.safe_margin", low=0, high=0.5)
        if margin == 0.5:
            _fail(here + ".framing.safe_margin", "must leave a nonempty safe area")
        _boolean(framing["require_full"], here + ".framing.require_full")
        _number(framing["min_visible_fraction"], here + ".framing.min_visible_fraction", low=0, high=1)
        narrative = _mapping(shot["narrative"], here + ".narrative", {"camera", "subject", "light", "material", "cut"})
        for field in narrative:
            _text(narrative[field], here + ".narrative." + field)
    if cursor != duration:
        _fail("shots", f"timeline ends at {cursor}, expected {duration}")
    if hold < shots[-1]["start"]:
        _fail("hold_start", "the final stable hold must be inside the last shot without a cut")
    local_hold = hold - shots[-1]["start"]
    _constant_after(shots[-1]["camera"]["keys"], local_hold, "final camera hold")
    for animation in shots[-1]["animations"]:
        _constant_after(animation["keys"], local_hold, f"final object {animation['object']} hold")

    provider = _mapping(data["provider"], "provider",
                        {"status", "name", "entry", "checked_at", "evidence", "max_seconds", "max_images",
                         "supports_video_reference", "label_syntax"})
    _choice(provider["status"], {"unverified", "verified"}, "provider.status")
    verified = provider["status"] == "verified"
    for field in ("name", "entry", "checked_at", "evidence", "label_syntax"):
        _text(provider[field], "provider." + field, empty=not verified)
    for field, integer, low in (("max_seconds", False, None), ("max_images", True, 0)):
        value = provider[field]
        if value is not None or verified:
            _number(value, "provider." + field, integer=integer, low=low, positive=field == "max_seconds")
    if provider["supports_video_reference"] is not None or verified:
        _boolean(provider["supports_video_reference"], "provider.supports_video_reference")


def _fixture_object(name: str, role: str, primitive: str, location: list,
                    dimensions: list, rationale: str, rotation: list | None = None) -> dict:
    return {"id": name, "role": role, "primitive": primitive, "location": location,
            "dimensions": dimensions, "rotation_deg": rotation or [0, 0, 0],
            "color": [0.83, 0.84, 0.85] if role == "product" else [0.72, 0.74, 0.76],
            "rationale": rationale}


def _fit_key(frame: int, height: float, lens: float, azimuth: float, elevation: float,
             *, target: list | None = None, roll: float = 0) -> dict:
    return {"frame": frame, "target": target or [0, 0, 0.9], "lens_mm": lens,
            "roll_deg": roll, "ease": "smootherstep",
            "fit": {"object": "product", "height_fraction": height, "azimuth_deg": azimuth,
                    "elevation_deg": elevation, "target_offset": [0, 0, 0]}}


def _vsub(a: list, b: list) -> list:
    return [x - y for x, y in zip(a, b)]


def _dot(a: list, b: list) -> float:
    return sum(x * y for x, y in zip(a, b))


def _cross(a: list, b: list) -> list:
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


def _unit(vector: list) -> list:
    length = math.sqrt(_dot(vector, vector))
    return [item / length for item in vector]


def _rotate(point: list, rotation: list) -> list:
    x, y, z = point
    rx, ry, rz = map(math.radians, rotation)
    y, z = y * math.cos(rx) - z * math.sin(rx), y * math.sin(rx) + z * math.cos(rx)
    x, z = x * math.cos(ry) + z * math.sin(ry), -x * math.sin(ry) + z * math.cos(ry)
    x, y = x * math.cos(rz) - y * math.sin(rz), x * math.sin(rz) + y * math.cos(rz)
    return [x, y, z]


def _fixture_mesh(obj: dict) -> tuple[list[list], list[list[int]]]:
    primitive = obj["primitive"]
    if primitive == "mesh":
        lower = [min(point[axis] for point in obj["vertices"]) for axis in range(3)]
        upper = [max(point[axis] for point in obj["vertices"]) for axis in range(3)]
        vertices = [[(point[axis] - (lower[axis] + upper[axis]) / 2) / (upper[axis] - lower[axis])
                     if upper[axis] != lower[axis] else 0 for axis in range(3)] for point in obj["vertices"]]
        faces = obj["faces"]
    elif primitive in {"cube", "plane"}:
        vertices = [[x, y, z] for x in (-.5, .5) for y in (-.5, .5) for z in (-.5, .5)]
        faces = [[0, 1, 3, 2], [4, 6, 7, 5], [0, 4, 5, 1], [2, 3, 7, 6], [0, 2, 6, 4], [1, 5, 7, 3]]
    elif primitive == "cylinder":
        vertices = [[.5 * math.cos(2 * math.pi * i / 24), .5 * math.sin(2 * math.pi * i / 24), z]
                    for z in (-.5, .5) for i in range(24)]
        faces = [[i, (i + 1) % 24, (i + 1) % 24 + 24, i + 24] for i in range(24)]
        faces += [list(range(24)), list(range(24, 48))]
    else:
        vertices = [[.5 * math.sin(math.pi * j / 12) * math.cos(2 * math.pi * i / 24),
                     .5 * math.sin(math.pi * j / 12) * math.sin(2 * math.pi * i / 24),
                     .5 * math.cos(math.pi * j / 12)] for j in range(13) for i in range(24)]
        faces = [[j * 24 + i, j * 24 + (i + 1) % 24, (j + 1) * 24 + (i + 1) % 24, (j + 1) * 24 + i]
                 for j in range(12) for i in range(24)]
    world = []
    for vertex in vertices:
        rotated = _rotate([item * size for item, size in zip(vertex, obj["dimensions"])], obj["rotation_deg"])
        world.append([value + origin for value, origin in zip(rotated, obj["location"])])
    return world, faces


_FONT = {
    "A": [14,17,17,31,17,17,17], "B": [30,17,17,30,17,17,30], "C": [14,17,16,16,16,17,14],
    "D": [30,17,17,17,17,17,30], "E": [31,16,16,30,16,16,31], "F": [31,16,16,30,16,16,16],
    "G": [14,17,16,23,17,17,15], "H": [17,17,17,31,17,17,17], "I": [31,4,4,4,4,4,31],
    "J": [7,2,2,2,2,18,12], "K": [17,18,20,24,20,18,17], "L": [16,16,16,16,16,16,31],
    "M": [17,27,21,21,17,17,17], "N": [17,25,21,19,17,17,17], "O": [14,17,17,17,17,17,14],
    "P": [30,17,17,30,16,16,16], "Q": [14,17,17,17,21,18,13], "R": [30,17,17,30,20,18,17],
    "S": [15,16,16,14,1,1,30], "T": [31,4,4,4,4,4,4], "U": [17,17,17,17,17,17,14],
    "V": [17,17,17,17,17,10,4], "W": [17,17,17,21,21,21,10], "X": [17,17,10,4,10,17,17],
    "Y": [17,17,10,4,4,4,4], "Z": [31,1,2,4,8,16,31], " ": [0]*7, "-": [0,0,0,31,0,0,0],
}


def _fixture_png(path: Path, layout: dict) -> None:
    """Independent analytic design projection, never a Blender render or AI art."""
    width, height = 360, 640
    pixels = bytearray([239, 240, 241] * width * height)
    depth_buffer = [math.inf] * (width * height)
    key = layout["camera"]["keys"][0]
    fit, target = key["fit"], key["target"]
    azimuth, elevation = math.radians(fit["azimuth_deg"]), math.radians(fit["elevation_deg"])
    outward = [math.sin(azimuth) * math.cos(elevation), -math.cos(azimuth) * math.cos(elevation), math.sin(elevation)]
    forward = [-component for component in outward]
    right = _unit(_cross(forward, [0, 0, 1]))
    up = _cross(right, forward)
    focal = key["lens_mm"] * width / layout["camera"]["sensor_width_mm"]
    mesh = [_fixture_mesh(obj) for obj in layout["objects"]]
    product = mesh[next(i for i, obj in enumerate(layout["objects"]) if obj["id"] == "product")][0]

    def project(point: list, distance: float) -> tuple[float, float, float]:
        relative = _vsub(point, [target[i] + outward[i] * distance for i in range(3)])
        depth = _dot(relative, forward)
        if depth <= .00001:
            return (0, 0, depth)
        return (width / 2 + _dot(relative, right) * focal / depth,
                height / 2 - _dot(relative, up) * focal / depth, depth)

    low, high = .01, 1.0
    def fits(distance: float) -> bool:
        points = [project(point, distance) for point in product]
        return min(point[2] for point in points) > 0 and max(p[1] for p in points) - min(p[1] for p in points) <= height * fit["height_fraction"]
    while not fits(high):
        high *= 2
    for _ in range(60):
        middle = (low + high) / 2
        if fits(middle):
            high = middle
        else:
            low = middle
    distance = high

    def paint(x: int, y: int, color: tuple) -> None:
        if 0 <= x < width and 0 <= y < height:
            offset = (y * width + x) * 3
            pixels[offset:offset + 3] = bytes(color)

    def polygon(points: list, color: tuple) -> None:
        y0, y1 = max(0, int(min(p[1] for p in points))), min(height - 1, math.ceil(max(p[1] for p in points)))
        for y in range(y0, y1 + 1):
            intersections = []
            for a, b in zip(points, points[1:] + points[:1]):
                if (a[1] <= y + .5 < b[1]) or (b[1] <= y + .5 < a[1]):
                    intersections.append(a[0] + (y + .5 - a[1]) * (b[0] - a[0]) / (b[1] - a[1]))
            intersections.sort()
            for start, end in zip(intersections[::2], intersections[1::2]):
                for x in range(max(0, math.ceil(start)), min(width, math.ceil(end))):
                    paint(x, y, color)

    def geometry(points: list, color: tuple) -> None:
        # Perspective-correct depth prevents a large floor/backdrop polygon
        # from covering a nearer object merely because its mean depth is small.
        for number in range(1, len(points) - 1):
            a, b, c = points[0], points[number], points[number + 1]
            area = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
            if abs(area) < 1e-12:
                continue
            x0, x1 = max(0, math.floor(min(a[0], b[0], c[0]))), min(width - 1, math.ceil(max(a[0], b[0], c[0])))
            y0, y1 = max(0, math.floor(min(a[1], b[1], c[1]))), min(height - 1, math.ceil(max(a[1], b[1], c[1])))
            for y in range(y0, y1 + 1):
                for x in range(x0, x1 + 1):
                    w0 = ((b[0] - x - .5) * (c[1] - y - .5) - (b[1] - y - .5) * (c[0] - x - .5)) / area
                    w1 = ((c[0] - x - .5) * (a[1] - y - .5) - (c[1] - y - .5) * (a[0] - x - .5)) / area
                    w2 = 1 - w0 - w1
                    if min(w0, w1, w2) >= -1e-10:
                        depth = 1 / (w0 / a[2] + w1 / b[2] + w2 / c[2])
                        offset = y * width + x
                        if depth < depth_buffer[offset]:
                            depth_buffer[offset] = depth
                            paint(x, y, color)

    faces_to_draw = []
    light = _unit([-.7, -1, 2])
    for object_index, (vertices, faces) in enumerate(mesh):
        projected = [project(point, distance) for point in vertices]
        for face in faces:
            points = [projected[index] for index in face]
            if min(point[2] for point in points) <= .00001:
                continue
            normal = _cross(_vsub(vertices[face[1]], vertices[face[0]]), _vsub(vertices[face[2]], vertices[face[0]]))
            norm = math.sqrt(_dot(normal, normal))
            shade = .74 + .22 * abs(_dot([v / norm for v in normal], light)) if norm else .84
            color = tuple(min(245, max(110, int(channel * 255 * shade))) for channel in layout["objects"][object_index]["color"])
            faces_to_draw.append((sum(point[2] for point in points) / len(points), points, color))
    for _, points, color in sorted(faces_to_draw, reverse=True, key=lambda item: item[0]):
        geometry(points, color)

    def label(text: str, x: int, y: int, size: int = 2) -> None:
        for char in text:
            for row, bits in enumerate(_FONT[char]):
                for col in range(5):
                    if bits & (1 << (4 - col)):
                        for yy in range(size):
                            for xx in range(size):
                                paint(x + col * size + xx, y + row * size + yy, (35, 40, 45))
            x += 6 * size
    polygon([(0, 0), (width, 0), (width, 48), (0, 48)], (250, 221, 125))
    polygon([(0, height - 49), (width, height - 49), (width, height), (0, height)], (250, 221, 125))
    label("TECHNICAL FIXTURE", 78, 9)
    label("LAYOUT " + layout["id"], 130, 29)
    label("PROXY ONLY - NOT AI ART", 48, height - 38)
    label("INDEPENDENT DESIGN PROJECTION", 7, height - 19)
    raw = b"".join(b"\x00" + bytes(pixels[y * width * 3:(y + 1) * width * 3]) for y in range(height))
    def chunk(kind: bytes, payload: bytes) -> bytes:
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload) & 0xffffffff)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    png += chunk(b"tEXt", b"Description\x00Synthetic technical fixture; analytic projection, not AI art or customer product")
    png += chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")
    with path.open("xb") as handle:
        handle.write(png)


def create_fixture(destination: str | Path) -> Path:
    """Create an external, branded-as-fixture 15 s / 9-shot / two-layout input."""
    target = Path(destination).resolve()
    package = Path(__file__).resolve().parent.parent
    if target.is_relative_to(package):
        _fail("fixture output", "generated fixtures must stay outside the installed/source Skill package")
    contract_path = target / "fixture.json"
    outputs = [contract_path, target / "layout-A.png", target / "layout-B.png"]
    if any(path.exists() or path.is_symlink() for path in outputs):
        _fail("fixture output", "refusing to overwrite an existing fixture or layout asset; choose a new directory")
    if target.exists() and not target.is_dir():
        _fail("fixture output", "expected a directory")
    target.mkdir(parents=True, exist_ok=True)
    common_product = _fixture_object("product", "product", "cube", [0, 0, .9], [.7, .48, 1.5],
                                     "Synthetic identity: plain upright cuboid; visible geometry and motion only, no brand or efficacy.")
    floor = _fixture_object("floor", "set", "plane", [0, 0, -.015], [8, 8, .02], "Neutral technical ground, not final material.")
    layouts = [
        {"id": "A", "image_asset": "layout-A", "rationale": "FIXTURE stepped vertical composition: cuboid proportions echoed by offset risers; central proxy remains readable.",
         "objects": [copy.deepcopy(common_product), copy.deepcopy(floor),
                     _fixture_object("plinth", "set", "cube", [0, 0, .075], [2.2, 1.4, .15], "Low shared support grounds the central proxy."),
                     _fixture_object("pillar", "set", "cube", [-1.3, .62, .65], [.38, .48, 1.3], "Offset vertical plane echoes the synthetic product's height."),
                     _fixture_object("accent", "material", "sphere", [1.05, .5, .38], [.6, .6, .6], "Abstract rounded counterpoint with independent transform; no fluid claim.")],
         "camera": {"sensor_width_mm": 36, "interpolation": "hermite", "keys": [_fit_key(0, .23, 45, -12, 12)]}},
        {"id": "B", "image_asset": "layout-B", "rationale": "FIXTURE asymmetric rounded field: circular pedestal and separated spherical accents contrast the same cuboid identity.",
         "objects": [copy.deepcopy(common_product), copy.deepcopy(floor),
                     _fixture_object("plinth", "set", "cylinder", [0, 0, .075], [1.2, 1.2, .15], "Circular support distinguishes a second reusable set."),
                     _fixture_object("pillar", "set", "sphere", [-1.18, .6, .6], [.72, .72, .72], "Floating abstract sphere at a separate depth plane."),
                     _fixture_object("accent", "material", "sphere", [1.12, .7, .35], [.46, .46, .46], "Small independent accent balances the larger left sphere.")],
         "camera": {"sensor_width_mm": 36, "interpolation": "hermite", "keys": [_fit_key(0, .22, 50, 10, 14)]}},
    ]
    arc = _fixture_object("arc-screen", "set", "mesh", [0, 1.15, .82], [3.25, .40, 1.6],
                          "FIXTURE seven-section low-poly arc backdrop; mesh bbox center is its location. Open surface, no imported product detail.")
    arc["vertices"] = [[(section - 3) / 3, .3 * ((section - 3) / 3) ** 2, z]
                       for section in range(7) for z in (-.5, .5)]
    arc["faces"] = [[section * 2, section * 2 + 2, section * 2 + 3, section * 2 + 1] for section in range(6)]
    layouts[1]["objects"].append(arc)
    assets = []
    for layout in layouts:
        path = safe_path(target, f"layout-{layout['id']}.png")
        _fixture_png(path, layout)
        assets.append({"id": layout["image_asset"], "role": "layout", "path": path.name, "sha256": sha256_file(path)})
    durations = [16, 14, 16, 14, 16, 18, 18, 28, 40]
    # Height, lens, azimuth and elevation vary independently; the backend fits
    # actual projected bounds, with no reusable constant camera distance.
    specs = [("A", .38, .48, 34, 40, -24, -5, 16, 10),
             ("A", .70, .80, 75, 82, 5, 22, 7, 12),
             ("B", .46, .52, 45, 52, -15, 12, 10, 7),
             ("B", .78, .83, 88, 93, 3, -10, 14, 9),
             ("A", .55, .60, 58, 64, 25, -20, 8, 15),
             ("B", .54, .56, 52, 62, -22, 5, 16, 9),
             ("A", .62, .58, 60, 55, -8, 18, 4, 20),
             ("B", .50, .46, 48, 52, 15, 0, 12, 8),
             ("A", .55, .48, 56, 60, -12, 0, 15, 9)]
    purposes = ["建立产品与阶梯置景的空间关系", "近景读取通用代理的体块转折", "用第二置景重建横向层次",
                "特写强调代理上部曲面边界", "绕行展示侧面与前后遮挡变化", "主体与抽象配景独立运动",
                "抬升机位读取顶部与台座关系", "整理构图并为片尾建立方向关系", "完成回正后稳定展示"]
    shots = []
    start = 0
    for index, (count, spec) in enumerate(zip(durations, specs)):
        layout_id, h0, h1, l0, l1, a0, a1, e0, e1 = spec
        end_motion = 24 if index == 8 else count - 1
        times = [0, end_motion // 3, 2 * end_motion // 3, end_motion]
        keys = []
        for key_index, (frame, fraction) in enumerate(zip(times, (0, 1/3, 2/3, 1))):
            bow = math.sin(math.pi * fraction)
            keys.append(_fit_key(frame, h0 + (h1 - h0) * fraction + .008 * bow,
                                 l0 + (l1 - l0) * fraction,
                                 a0 + (a1 - a0) * fraction + 2.1 * bow,
                                 e0 + (e1 - e0) * fraction + 1.4 * bow,
                                 roll=.4 * bow if index in (4, 6) else 0))
        if index == 8:
            keys.append({**copy.deepcopy(keys[-1]), "frame": count - 1})
        object_keys = []
        for frame in times:
            fraction = frame / end_motion
            rotation = -6 + 12 * fraction if index != 8 else -5 * (1 - fraction)
            object_keys.append({"frame": frame, "location": [0, 0, .9],
                                "rotation_deg": [0, 0, rotation], "scale": [1, 1, 1], "ease": "smootherstep"})
        if index == 8:
            object_keys.append({**copy.deepcopy(object_keys[-1]), "frame": count - 1})
        animations = [{"object": "product", "interpolation": "hermite", "keys": object_keys}]
        if index in (2, 5, 7):
            accent = next(obj for layout in layouts if layout["id"] == layout_id for obj in layout["objects"] if obj["id"] == "accent")
            accent_keys = []
            for frame in times:
                fraction = frame / end_motion
                location = copy.deepcopy(accent["location"])
                location[0] += .08 * math.sin(math.pi * fraction)
                location[2] += .12 * fraction
                accent_keys.append({"frame": frame, "location": location, "rotation_deg": [0, 0, 0],
                                    "scale": [1, 1, 1], "ease": "smoothstep"})
            animations.append({"object": "accent", "interpolation": "hermite", "keys": accent_keys})
        shots.append({"id": f"S{index + 1:02d}", "layout": layout_id, "start": start, "end": start + count,
                      "purpose": purposes[index], "entry_state": "合成代理与当前共享置景建立明确起始状态。",
                      "exit_state": "独立镜头终态；硬切关系由下镜重新建立。" if index < 8 else "第24帧前结束全部运动，保持16帧稳定展示。",
                      "transition": {"kind": "hard_cut", "relation": "display_time" if index == 8 else "association",
                                     "description": "明确硬切；通过体块或视线方向建立联想，不声称物理无缝连续。"},
                      "camera": {"sensor_width_mm": 36, "interpolation": "hermite", "keys": keys},
                      "animations": animations,
                      "framing": {"object": "product", "min_height": .10, "max_height": .78 if index == 8 else 1.2,
                                  "safe_margin": .035, "require_full": index == 8, "min_visible_fraction": .65},
                      "narrative": {"camera": "按实际拟合关键机位复合绕行、抬升与改变画面占比，读取真实焦段和运动时序。",
                                    "subject": "无品牌长方体代理独立回转；独立球体运动只在指定镜头出现。",
                                    "light": "最终意图为宽柔主光与窄反射条逐渐扫过侧面；技术白模预演不验证真实灯光。",
                                    "material": "技术测试只有刚体代理，不模拟配方、流体或产品功效。",
                                    "cut": "用明确硬切连接独立镜头；片尾先停运动再留稳定展示时间。"}})
        start += count
    data = {"schema": SCHEMA, "id": "synthetic-15s-nine-shot", "fixture": True, "fps": 12,
            "duration_frames": 180, "resolution": [180, 320], "hold_start": 164, "assets": assets,
            "creative": {"concept": "TECHNICAL FIXTURE：同一无品牌长方体在两套几何置景中完成十五秒九镜头代理预演。",
                         "product_facts": "仅有合成长方体尺寸与可见几何事实；不是客户素材或真实产品。",
                         "unknowns": "真实成分、功效、包装文字、最终表面及真实AI布局质量均未测试。",
                         "look": "FIXTURE技术白模；真实风格图缺席，本测试不证明最终影调。",
                         "lighting": "软主光与窄条反射为文字设计意图；Workbench技术预览不验证照明结果。",
                         "material_process": "刚体代理只测试变换，不声称真实流体、黏度或制造过程。",
                         "identity": "两个布局共用相同无品牌长方体尺寸；产品中心与占位一致。",
                         "text_lock": "无真实产品文字；输出必须保留TECHNICAL FIXTURE标记。",
                         "photography": "先选信息目的，再以投影占比、传感器、焦段及非共线机位几何拟合摄影。",
                         "scene_design": "布局A复用阶梯与竖向配景；布局B复用圆形台座、球体与七截面弧面屏风。两套均保留同一中央产品占位。",
                         "previs_rules": "白模只约束空间占位、摄影、代理动作及剪辑；真正外观须由获授权的产品与影调图另行锁定。",
                         "visibility": "fixture没有真实文字；未来产品必须在最终稳定段提供足够画面占比并抑制遮挡和刺眼反光。"},
            "layouts": layouts, "shots": shots,
            "provider": {"status": "unverified", "name": "", "entry": "", "checked_at": "", "evidence": "",
                         "max_seconds": None, "max_images": None, "supports_video_reference": None, "label_syntax": ""}}
    validate_contract(data, target, verify_assets=True)
    dump_json(contract_path, data)
    return contract_path
