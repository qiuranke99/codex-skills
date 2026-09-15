"""Portable behavior tests. Synthetic fixtures only; no Blender, browser or upload.

Run: python -B -X utf8 -m unittest discover -s scripts -p 'test_*.py' -v
The media/compiler tests mock the completed-media boundary explicitly.  They do
not stand in for a Blender run, actual playback, or independent visual review.
"""

from __future__ import annotations

import copy
import io
import json
import math
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock

import core
from core import (ContractError, contract_digest, create_fixture, dump_json,
                  ease_value, interpolate_keys, load_contract, safe_path,
                  sha256_file, validate_contract)
import runtime


def replace(data, path, value):
    node = data
    for component in path[:-1]:
        node = node[component]
    node[path[-1]] = value


class FixtureCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source_temp = tempfile.TemporaryDirectory(prefix="tvc-synthetic-tests-")
        cls.source = Path(cls.source_temp.name)
        cls.source_contract = create_fixture(cls.source / "fixture")
        cls.original = load_contract(cls.source_contract)

    @classmethod
    def tearDownClass(cls):
        cls.source_temp.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="tvc-test-case-")
        self.root = Path(self.temp.name)
        self.fixture = self.root / "fixture"
        shutil.copytree(self.source_contract.parent, self.fixture)
        self.path = self.fixture / "fixture.json"
        self.data = copy.deepcopy(self.original)

    def tearDown(self):
        self.temp.cleanup()

    def invalid(self, data=None, text=None, verify_assets=False):
        with self.assertRaises(ContractError) as caught:
            validate_contract(data if data is not None else self.data,
                              self.fixture, verify_assets=verify_assets)
        self.assertTrue(str(caught.exception).strip())
        if text:
            self.assertIn(text, str(caught.exception))


class ContractTests(FixtureCase):
    def test_generated_fixture_has_actual_images_and_nine_variable_shots(self):
        result = load_contract(self.path)
        self.assertEqual(result["duration_frames"] / result["fps"], 15)
        self.assertEqual(result["resolution"], [180, 320])
        self.assertEqual(len(result["shots"]), 9)
        self.assertEqual(len(result["layouts"]), 2)
        self.assertGreater(len({s["end"] - s["start"] for s in result["shots"]}), 2)
        self.assertEqual(result["duration_frames"] - result["hold_start"], 16)
        self.assertTrue(all(sum(s["layout"] == layout["id"] for s in result["shots"]) > 1 for layout in result["layouts"]))
        self.assertTrue(any(len(s["animations"]) > 1 for s in result["shots"]))
        self.assertTrue(any(o["primitive"] == "mesh" for layout in result["layouts"] for o in layout["objects"]))
        for asset in result["assets"]:
            image = safe_path(self.fixture, asset["path"], True)
            self.assertEqual(image.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")
            self.assertIn(b"Synthetic technical fixture", image.read_bytes())
            self.assertEqual(sha256_file(image), asset["sha256"])
        self.assertNotEqual(result["assets"][0]["sha256"], result["assets"][1]["sha256"])

    def test_fixture_refuses_overwrite_without_altering_files(self):
        before = {p.name: sha256_file(p) for p in self.fixture.iterdir() if p.is_file()}
        with self.assertRaises(ContractError):
            create_fixture(self.fixture)
        self.assertEqual(before, {p.name: sha256_file(p) for p in self.fixture.iterdir() if p.is_file()})

    def test_fixture_refuses_output_under_its_package(self):
        target = Path(core.__file__).resolve().parent.parent / "test-output-must-not-exist"
        self.assertFalse(target.exists())
        with self.assertRaises(ContractError):
            create_fixture(target)
        self.assertFalse(target.exists())

    def test_production_requires_product_look_and_layout_assets(self):
        self.data["fixture"] = False
        self.invalid(text="required asset roles")
        for role in ("product", "look"):
            self.data["assets"].append(dict(self.data["assets"][0], id=role + "-test", role=role))
        validate_contract(self.data, self.fixture, verify_assets=True)

    def test_all_key_numeric_types_reject_bool_nan_and_infinities(self):
        paths = [
            ("fps",), ("duration_frames",), ("resolution", 0), ("hold_start",),
            ("layouts", 0, "objects", 0, "location", 0),
            ("layouts", 0, "objects", 0, "dimensions", 0),
            ("layouts", 0, "objects", 0, "rotation_deg", 0),
            ("layouts", 0, "objects", 0, "color", 0),
            ("layouts", 0, "camera", "sensor_width_mm"),
            ("shots", 0, "start"), ("shots", 0, "end"),
            ("shots", 0, "camera", "keys", 0, "frame"),
            ("shots", 0, "camera", "keys", 0, "lens_mm"),
            ("shots", 0, "camera", "keys", 0, "roll_deg"),
            ("shots", 0, "camera", "keys", 0, "target", 0),
            ("shots", 0, "camera", "keys", 0, "fit", "height_fraction"),
            ("shots", 0, "camera", "keys", 0, "fit", "azimuth_deg"),
            ("shots", 0, "camera", "keys", 0, "fit", "elevation_deg"),
            ("shots", 0, "camera", "keys", 0, "fit", "target_offset", 0),
            ("shots", 0, "animations", 0, "keys", 0, "location", 0),
            ("shots", 0, "animations", 0, "keys", 0, "rotation_deg", 0),
            ("shots", 0, "animations", 0, "keys", 0, "scale", 0),
            ("shots", 0, "framing", "min_height"),
            ("shots", 0, "framing", "max_height"),
            ("shots", 0, "framing", "safe_margin"),
            ("shots", 0, "framing", "min_visible_fraction"),
            ("layouts", 1, "objects", -1, "vertices", 0, 0),
            ("provider", "max_images"), ("provider", "max_seconds"),
        ]
        for path in paths:
            for value in (True, float("nan"), float("inf"), -float("inf")):
                with self.subTest(path=path, value=value):
                    data = copy.deepcopy(self.original)
                    replace(data, path, value)
                    self.invalid(data)

    def test_malformed_nested_structures_raise_contract_error(self):
        paths = [("assets",), ("assets", 0), ("layouts",), ("layouts", 0),
                 ("layouts", 0, "objects"), ("layouts", 0, "objects", 0),
                 ("layouts", 0, "camera"), ("shots",), ("shots", 0),
                 ("shots", 0, "camera", "keys"), ("shots", 0, "camera", "keys", 0),
                 ("shots", 0, "camera", "keys", 0, "fit"),
                 ("shots", 0, "animations"), ("shots", 0, "animations", 0),
                 ("shots", 0, "animations", 0, "keys", 0),
                 ("shots", 0, "framing"), ("shots", 0, "narrative"),
                 ("shots", 0, "transition"), ("creative",), ("provider",)]
        for path in paths:
            for value in (None, [], "invalid"):
                if path == ("shots", 0, "animations") and value == []:
                    continue  # Unanimated shots intentionally use an empty list.
                with self.subTest(path=path, value=value):
                    data = copy.deepcopy(self.original)
                    replace(data, path, value)
                    self.invalid(data)

    def test_missing_and_unknown_fields_are_readable_errors(self):
        for path in [(), ("creative",), ("layouts", 0, "objects", 0),
                     ("shots", 0, "camera", "keys", 0), ("provider",)]:
            for operation in ("missing", "unknown"):
                with self.subTest(path=path, operation=operation):
                    data = copy.deepcopy(self.original)
                    node = data
                    for component in path:
                        node = node[component]
                    if operation == "missing":
                        required = "concept" if path == ("creative",) else "frame" if path[-1:] == (0,) and "frame" in node else next(iter(node))
                        node.pop(required)
                    else:
                        node["misspelled_field"] = 1
                    self.invalid(data, text="unknown" if operation == "unknown" else None)

    def test_references_uniqueness_and_mandatory_layout_image(self):
        cases = [(("layouts", 0, "image_asset"), "unknown"),
                 (("layouts", 0, "image_asset"), None),
                 (("shots", 0, "layout"), "missing-layout"),
                 (("shots", 0, "framing", "object"), "missing-product"),
                 (("shots", 0, "animations", 0, "object"), "missing-object"),
                 (("shots", 0, "camera", "keys", 0, "fit", "object"), "missing-object"),
                 (("assets", 1, "id"), "layout-A"),
                 (("layouts", 1, "id"), "A"),
                 (("layouts", 1, "id"), "a"),
                 (("layouts", 0, "objects", 1, "id"), "product"),
                 (("shots", 1, "id"), "S01"), (("shots", 1, "id"), "s01")]
        for path, value in cases:
            with self.subTest(path=path):
                data = copy.deepcopy(self.original)
                replace(data, path, value)
                self.invalid(data)
        self.data["assets"][0]["role"] = "art"
        self.invalid(text="layout image")

    def test_asset_and_shot_ids_cannot_collide_with_generated_video_namespace(self):
        for asset_id in ("PREVIS-S01", "previs-custom", "Previs-FULL"):
            with self.subTest(asset_id=asset_id):
                data = copy.deepcopy(self.original)
                old_id = data["assets"][0]["id"]
                data["assets"][0]["id"] = asset_id
                for layout in data["layouts"]:
                    if layout["image_asset"] == old_id:
                        layout["image_asset"] = asset_id
                self.invalid(data)
        for shot_id in ("FULL", "full", "Full"):
            with self.subTest(shot_id=shot_id):
                data = copy.deepcopy(self.original)
                data["shots"][0]["id"] = shot_id
                self.invalid(data)

    def test_changed_missing_and_nonimage_layout_assets(self):
        asset = self.fixture / self.data["assets"][0]["path"]
        asset.write_bytes(b"modified asset")
        self.invalid(text="hash mismatch", verify_assets=True)
        self.data["assets"][0]["sha256"] = sha256_file(asset)
        self.invalid(text="actual PNG", verify_assets=True)
        asset.unlink()
        self.invalid(text="cannot resolve", verify_assets=True)

    def test_timeline_rejects_gaps_overlaps_zero_length_and_incomplete_coverage(self):
        cases = [(("shots", 1, "start"), 17), (("shots", 1, "start"), 15),
                 (("shots", 0, "end"), 0), (("shots", 0, "start"), -1),
                 (("duration_frames",), 181), (("duration_frames",), 179),
                 (("shots", 0, "end"), 16.5)]
        for path, value in cases:
            with self.subTest(path=path, value=value):
                data = copy.deepcopy(self.original)
                replace(data, path, value)
                self.invalid(data)

    def test_keys_require_exact_local_coverage_sorted_unique_bounds(self):
        for owner in (("camera",), ("animations", 0)):
            for key_index, bad in ((0, -1), (0, 1), (-1, 16), (-1, 14), (1, 0), (1, 2.5)):
                with self.subTest(owner=owner, index=key_index, value=bad):
                    data = copy.deepcopy(self.original)
                    replace(data, ("shots", 0) + owner + ("keys", key_index, "frame"), bad)
                    self.invalid(data)
        self.data["layouts"][0]["camera"]["keys"].append(copy.deepcopy(self.data["layouts"][0]["camera"]["keys"][0]))
        self.invalid(text="strictly increasing")

    def test_final_hold_requires_duration_and_true_camera_object_stability(self):
        for mutation in ("duration", "cut", "lens", "target", "object", "scale", "late_stop"):
            with self.subTest(mutation=mutation):
                data = copy.deepcopy(self.original)
                if mutation == "duration":
                    data["hold_start"] = 170
                elif mutation == "cut":
                    data["hold_start"] = 130
                elif mutation == "lens":
                    data["shots"][-1]["camera"]["keys"][-1]["lens_mm"] += 1
                elif mutation == "target":
                    data["shots"][-1]["camera"]["keys"][-1]["target"][0] += .1
                elif mutation in ("object", "scale"):
                    field = "location" if mutation == "object" else "scale"
                    data["shots"][-1]["animations"][0]["keys"][-1][field][0] += .01
                else:
                    data["shots"][-1]["camera"]["keys"][-2]["frame"] += 1
                self.invalid(data, text="hold")

    def test_camera_position_and_fit_modes_and_variable_sensor_are_valid(self):
        for key in self.data["shots"][0]["camera"]["keys"]:
            key.pop("fit")
            key["position"] = [key["frame"] / 20, -3, 1.4]
        self.data["shots"][0]["camera"]["sensor_width_mm"] = 24.9
        validate_contract(self.data)
        for mutation in ("both", "neither", "same_target", "zero_lens", "zero_sensor"):
            data = copy.deepcopy(self.data)
            camera = data["shots"][0]["camera"]
            key = camera["keys"][0]
            if mutation == "both":
                key["fit"] = copy.deepcopy(self.original["shots"][0]["camera"]["keys"][0]["fit"])
            elif mutation == "neither":
                key.pop("position")
            elif mutation == "same_target":
                key["position"] = key["target"]
            elif mutation == "zero_lens":
                key["lens_mm"] = 0
            else:
                camera["sensor_width_mm"] = 0
            with self.subTest(mutation=mutation):
                self.invalid(data)

    def test_mesh_allows_planar_and_rejects_invalid_index_geometry_and_size(self):
        mesh = self.data["layouts"][1]["objects"][-1]
        mesh["vertices"] = [[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0]]
        mesh["faces"] = [[0, 1, 2, 3]]
        validate_contract(self.data)
        cases = [("faces", [[0, 1, True]]), ("faces", [[0, 1, 4]]),
                 ("faces", [[0, 1, -1]]), ("faces", [[0, 1, 2.0]]),
                 ("faces", [[0, 1, 1]]), ("faces", [[0, 1]]),
                 ("vertices", [[0, 0, 0], [1, 0, 0], [2, 0, 0]]),
                 ("vertices", [[0, 0, 0], [1, 1, 0], [2, 2, 0], [3, 3, 0]]),
                 ("vertices", [[0, 0], [1, 0], [1, 1]]),
                 ("vertices", [[0, 0, 0]] * 5001),
                 ("faces", [[0, 1, 2]] * 10001)]
        for field, value in cases:
            with self.subTest(field=field, size=len(value)):
                data = copy.deepcopy(self.data)
                data["layouts"][1]["objects"][-1][field] = value
                self.invalid(data)
        mesh["primitive"] = "cube"
        self.invalid(text="only supported")

    def test_positive_dimensions_scale_and_valid_framing(self):
        cases = [(("layouts", 0, "objects", 0, "dimensions", 1), 0),
                 (("shots", 0, "animations", 0, "keys", 0, "scale", 1), -1),
                 (("shots", 0, "framing", "safe_margin"), .5),
                 (("shots", 0, "framing", "min_visible_fraction"), 1.01),
                 (("shots", 0, "framing", "max_height"), .1),
                 (("shots", 0, "framing", "require_full"), 1)]
        for path, value in cases:
            with self.subTest(path=path):
                data = copy.deepcopy(self.original)
                replace(data, path, value)
                self.invalid(data)

    def test_interpolation_mode_and_optional_creative_fields(self):
        for field in ("scene_design", "previs_rules", "visibility"):
            self.data["creative"].pop(field)
        validate_contract(self.data)
        self.data["creative"]["scene_design"] = ""
        self.invalid(text="scene_design")
        for owner in ("camera", "animation"):
            data = copy.deepcopy(self.original)
            target = data["shots"][0]["camera"] if owner == "camera" else data["shots"][0]["animations"][0]
            target["interpolation"] = "bezier_magic"
            self.invalid(data, text="interpolation")

    def test_provider_unknown_and_verified_evidence_values(self):
        validate_contract(self.data)
        self.data["provider"]["status"] = "verified"
        self.invalid(text="provider")
        self.data["provider"] = {"status": "verified", "name": "SYNTHETIC ENTRY", "entry": "test-only",
                                 "checked_at": "2026-01-01", "evidence": "Synthetic test record, not real capabilities",
                                 "max_seconds": 15, "max_images": 0, "supports_video_reference": False,
                                 "label_syntax": "neutral"}
        validate_contract(self.data)
        for field, value in (("max_images", True), ("max_seconds", -1), ("supports_video_reference", 0), ("evidence", "")):
            data = copy.deepcopy(self.data)
            data["provider"][field] = value
            self.invalid(data, text="provider")

    def test_json_rejects_duplicate_nonfinite_and_invalid_encoding(self):
        for raw in ('{"schema":"x","schema":"y"}', '{"x":NaN}', '{"x":Infinity}', "[", "{}"):
            with self.subTest(raw=raw):
                self.path.write_text(raw, encoding="utf-8")
                with self.assertRaises(ContractError):
                    load_contract(self.path)
        self.path.write_bytes(b"\xff\xfeinvalid")
        with self.assertRaises(ContractError):
            load_contract(self.path)

    def test_digest_is_order_independent_sensitive_and_rejects_nonfinite(self):
        reordered = dict(reversed(list(self.data.items())))
        self.assertEqual(contract_digest(reordered), contract_digest(self.data))
        self.data["creative"]["concept"] += " changed"
        self.assertNotEqual(contract_digest(self.data), contract_digest(self.original))
        with self.assertRaises(ContractError):
            contract_digest({"x": math.inf})


class PathTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="tvc-path-tests-")
        self.root = Path(self.temp.name)
        (self.root / "root").mkdir()
        self.anchor = self.root / "root"

    def tearDown(self):
        self.temp.cleanup()

    def test_safe_nested_path_and_positional_must_exist(self):
        (self.anchor / "nested").mkdir()
        asset = self.anchor / "nested" / "image.png"
        asset.write_bytes(b"test")
        self.assertEqual(safe_path(self.anchor, "nested/image.png", True), asset.resolve())
        self.assertEqual(safe_path(self.anchor, "nested\\image.png", True), asset.resolve())

    def test_rejects_traversal_absolute_ads_devices_and_ambiguous_components(self):
        paths = ["../outside", "nested/../../outside", "nested/../file", "/absolute", "\\absolute",
                 "C:/absolute", "C:drive-relative", "\\\\host\\share\\file", "file.png:secret", "http://host/file",
                 "file:stream:$DATA", "CON", "nul.png", "nested/LPT9.txt", "a/./b", "a//b", "a/", " a. ",
                 "name.", "name ", "\x00.png", "a\nb", "foo?.png", "foo*.png", "", None, 1, []]
        for path in paths:
            with self.subTest(path=path):
                with self.assertRaises(ContractError):
                    safe_path(self.anchor, path)

    def test_existing_and_nonexistent_symlink_escape_rejected(self):
        outside = self.root / "outside"
        outside.mkdir()
        (outside / "existing.txt").write_text("outside", encoding="utf-8")
        try:
            (self.anchor / "link").symlink_to(outside, target_is_directory=True)
        except OSError as exc:
            self.skipTest(f"Platform does not permit symlink creation: {exc}")
        for relative, existing in (("link/existing.txt", True), ("link/new.txt", False)):
            with self.subTest(relative=relative):
                with self.assertRaises(ContractError):
                    safe_path(self.anchor, relative, existing)

    def test_internal_symlink_allowed_and_missing_asset_rejected(self):
        real = self.anchor / "real"
        real.mkdir()
        (real / "file.txt").write_text("inside", encoding="utf-8")
        try:
            (self.anchor / "alias").symlink_to(real, target_is_directory=True)
        except OSError as exc:
            self.skipTest(f"Platform does not permit symlink creation: {exc}")
        self.assertEqual(safe_path(self.anchor, "alias/file.txt", True), real / "file.txt")
        with self.assertRaises(ContractError):
            safe_path(self.anchor, "missing.txt", True)


class MotionTests(unittest.TestCase):
    def test_ease_functions_expected_values_and_invalid_inputs(self):
        self.assertEqual(ease_value("linear", .25), .25)
        self.assertEqual(ease_value("smoothstep", .25), .15625)
        self.assertEqual(ease_value("smootherstep", .5), .5)
        for name in ("linear", "smoothstep", "smootherstep"):
            self.assertEqual(ease_value(name, 0), 0)
            self.assertEqual(ease_value(name, 1), 1)
        for name, value in (("ease-in-out", .5), ("linear", True), ("linear", math.inf),
                            ("linear", -.1), ("linear", 1.1)):
            with self.assertRaises(ContractError):
                ease_value(name, value)

    def test_segment_uses_left_key_ease_and_interpolates_nested_numeric_values(self):
        keys = [{"frame": 0, "ease": "smoothstep", "position": [0, 2, 4], "nested": {"lens": 40}, "id": "same"},
                {"frame": 4, "ease": "linear", "position": [4, 6, 8], "nested": {"lens": 80}, "id": "same"}]
        state = interpolate_keys(keys, 1, "segment")
        self.assertEqual(state["position"], [.625, 2.625, 4.625])
        self.assertEqual(state["nested"]["lens"], 46.25)
        self.assertEqual(state["id"], "same")
        self.assertNotIn("frame", state)
        self.assertNotIn("ease", state)

    def test_hermite_nonuniform_noncollinear_junction_velocity_is_continuous_nonzero(self):
        keys = [{"frame": t, "position": p, "target": [p[0] / 2, 0, 1], "lens_mm": 35 + p[0], "roll_deg": p[1]}
                for t, p in [(0, [0, 0, 0]), (3, [1, 2, 1]), (9, [4, 3, 5]), (14, [8, 7, 9])]]
        epsilon = 1e-5
        for time in (3, 9):
            at = interpolate_keys(keys, time)
            left = interpolate_keys(keys, time - epsilon)
            right = interpolate_keys(keys, time + epsilon)
            before = [(a-b) / epsilon for a, b in zip(at["position"], left["position"])]
            after = [(b-a) / epsilon for a, b in zip(at["position"], right["position"])]
            self.assertGreater(math.sqrt(sum(v*v for v in before)), .1)
            for a, b in zip(before, after):
                self.assertAlmostEqual(a, b, delta=2e-5)
            for field in ("lens_mm", "roll_deg"):
                self.assertAlmostEqual((at[field]-left[field])/epsilon, (right[field]-at[field])/epsilon, delta=2e-5)

    def test_hermite_endpoints_and_repeated_channel_hold_have_zero_speed(self):
        keys = [{"frame": 0, "x": 0, "rotation_deg": [0, 0, 0]},
                {"frame": 5, "x": 2, "rotation_deg": [0, 0, 25]},
                {"frame": 11, "x": 4, "rotation_deg": [0, 0, 40]},
                {"frame": 20, "x": 4, "rotation_deg": [0, 0, 40]}]
        for time in (11, 11.01, 13.5, 19.99, 20, 30):
            self.assertEqual(interpolate_keys(keys, time), {"x": 4, "rotation_deg": [0, 0, 40]})
        epsilon = 1e-5
        self.assertAlmostEqual(interpolate_keys(keys, epsilon, endpoint_mode="stop")["x"] / epsilon, 0, delta=1e-5)
        self.assertAlmostEqual((4 - interpolate_keys(keys, 11-epsilon)["x"]) / epsilon, 0, delta=1e-5)

    def test_continue_endpoint_preserves_cut_momentum_and_stop_is_explicit(self):
        keys = [{"frame": 0, "x": 0}, {"frame": 4, "x": 2}, {"frame": 10, "x": 8}]
        epsilon = 1e-5
        self.assertAlmostEqual(interpolate_keys(keys, epsilon)["x"] / epsilon, .5, delta=1e-5)
        self.assertAlmostEqual((8-interpolate_keys(keys, 10-epsilon)["x"])/epsilon, 1, delta=1e-5)
        self.assertAlmostEqual((8-interpolate_keys(keys, 10-epsilon, endpoint_mode="stop")["x"])/epsilon, 0, delta=1e-5)
        with self.assertRaises(ContractError):
            interpolate_keys(keys, 2, endpoint_mode="automatic")

    def test_angles_do_not_implicitly_wrap_and_clamps_do_not_alias_inputs(self):
        keys = [{"frame": 0, "rotation_deg": [0, 0, 350]}, {"frame": 10, "rotation_deg": [0, 0, 10]}]
        self.assertEqual(interpolate_keys(keys, 5, "segment")["rotation_deg"][2], 180)
        state = interpolate_keys(keys, -1)
        state["rotation_deg"][2] = -99
        self.assertEqual(keys[0]["rotation_deg"][2], 350)
        self.assertEqual(interpolate_keys(keys, 11)["rotation_deg"][2], 10)

    def test_interpolation_rejects_bad_modes_times_and_mismatched_fields(self):
        for keys, frame, mode in [([], 0, "hermite"), ([{}], 0, "hermite"),
                                 ([{"frame": 0}, {"frame": 0}], 0, "hermite"),
                                 ([{"frame": 0}, {"frame": 1}], math.nan, "hermite"),
                                 ([{"frame": 0}, {"frame": 1}], .5, "bezier"),
                                 ([{"frame": 0, "x": [0, 1]}, {"frame": 1, "x": [0]}], .5, "hermite"),
                                 ([{"frame": 0, "position": [0, 0, 1]}, {"frame": 1, "fit": {"x": 1}}], .5, "hermite"),
                                 ([{"frame": 0, "x": 0}, {"frame": 1, "x": math.inf}], .5, "hermite")]:
            with self.subTest(keys=keys, frame=frame, mode=mode):
                with self.assertRaises(ContractError):
                    interpolate_keys(keys, frame, mode)


class RuntimeTests(FixtureCase):
    def lane(self, name="lane"):
        lane = self.root / name
        runtime.prepare(self.path, lane, name)
        return lane

    def test_prepare_copies_hash_bound_inputs_without_changing_originals(self):
        before = {p.name: sha256_file(p) for p in self.fixture.iterdir()}
        lane = self.lane()
        _, data, manifest = runtime.context(lane)
        self.assertEqual(manifest["source_contract_sha256"], contract_digest(self.original))
        self.assertEqual(manifest["contract_sha256"], contract_digest(data))
        for original, copied in zip(self.original["assets"], data["assets"]):
            self.assertEqual(copied["path"], "inputs/" + original["path"])
            self.assertEqual(sha256_file(safe_path(lane, copied["path"], True)), original["sha256"])
        self.assertEqual(before, {p.name: sha256_file(p) for p in self.fixture.iterdir()})
        job = runtime.read_json(lane / "job.json")
        self.assertEqual(Path(job["lane_root"]), lane.resolve())
        self.assertEqual(job["contract_sha256"], contract_digest(data))

    def test_prepare_rejects_invalid_input_before_making_lane(self):
        self.data["shots"][1]["start"] += 1
        dump_json(self.path, self.data)
        target = self.root / "must-not-exist"
        with self.assertRaises(ContractError):
            runtime.prepare(self.path, target, "invalid")
        self.assertFalse(target.exists())

    def test_prepare_rejects_package_output_duplicate_lane_and_unsafe_id(self):
        target = runtime.PACKAGE / "test-output-must-not-exist"
        with self.assertRaises(ContractError):
            runtime.prepare(self.path, target, "test")
        self.assertFalse(target.exists())
        lane = self.lane()
        before = sha256_file(lane / "lane.json")
        with self.assertRaises(ContractError):
            runtime.prepare(self.path, lane, "test")
        self.assertEqual(before, sha256_file(lane / "lane.json"))
        for name in ("../../bad", "/bad", "bad:stream", "bad name"):
            with self.subTest(name=name), self.assertRaises(ContractError):
                runtime.prepare(self.path, self.root / "bad", name)
        self.assertFalse((self.root / "bad").exists())

    def test_prepared_scene_or_worker_or_copied_asset_change_is_rejected(self):
        for kind in ("scene", "worker", "asset"):
            with self.subTest(kind=kind):
                lane = self.lane("lane-" + kind)
                if kind == "scene":
                    data = load_contract(lane / "scene.json")
                    data["creative"]["concept"] += " changed"
                    dump_json(lane / "scene.json", data)
                elif kind == "worker":
                    with (lane / "code" / "blender_worker.py").open("a", encoding="utf-8") as handle:
                        handle.write("\n# changed test worker\n")
                else:
                    (lane / "inputs" / "layout-A.png").write_bytes(b"changed")
                with self.assertRaises(ContractError):
                    runtime.context(lane)

    def test_production_full_build_requires_layout_review_but_layout_mode_prepares(self):
        data = copy.deepcopy(self.data)
        data["fixture"] = False
        data["assets"].extend([dict(data["assets"][0], id=role + "-test", role=role) for role in ("product", "look")])
        dump_json(self.path, data)
        out = self.root / "full-build"
        with self.assertRaises(ContractError):
            runtime.prepare(self.path, out, "full-build")
        self.assertFalse(out.exists())
        preview = self.root / "layout-preview"
        runtime.prepare(self.path, preview, "layout-preview", mode="layout")
        self.assertEqual(runtime.read_json(preview / "job.json")["mode"], "layout")

    def test_cli_returns_machine_readable_success_and_validation_error(self):
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = runtime.main(["validate", str(self.path)])
        self.assertEqual(code, 0)
        self.assertTrue(json.loads(stdout.getvalue())["valid"])
        self.data["fps"] = True
        dump_json(self.path, self.data)
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = runtime.main(["validate", str(self.path)])
        self.assertEqual(code, 2)
        self.assertIn("fps", json.loads(stderr.getvalue())["error"])

    def mock_media(self, lane):
        """Explicit in-memory completed-media boundary for text-only tests."""
        _, data, manifest = runtime.context(lane)
        shots = []
        for shot in data["shots"]:
            samples = [{"frame": frame, "camera_position": [frame / 100, -2.5, 1.1], "lens_mm": 48 + frame / 20,
                        "bbox": [.25, .2, .75, .8], "objects": {"product": {"location": [0, 0, .9]}}}
                       for frame in range(shot["end"] - shot["start"])]
            shots.append({"id": shot["id"], "samples": samples})
        report = {"shots": shots}
        clips = [{"id": s["id"], "path": str(lane / (s["id"] + ".mp4")), "sha256": "a" * 64} for s in data["shots"]]
        dump_json(lane / "media-report.json", {"clips": clips, "full": {"path": str(lane / "previs.mp4"), "sha256": "b" * 64}})
        binding = {"scene.json": sha256_file(lane / "scene.json"), "mock_only": "No actual media rendered"}
        return data, manifest, report, binding

    def test_compile_requires_review_unless_explicit_draft_and_keeps_neutral_roles(self):
        lane = self.lane()
        data, manifest, report, binding = self.mock_media(lane)
        with mock.patch.object(runtime, "inspect", return_value={"binding": binding}), \
             mock.patch.object(runtime, "checked_backend", return_value=(lane, data, manifest, report)):
            with self.assertRaises(ContractError):
                runtime.compile_prompt(lane)
            self.assertFalse((lane / "delivery").exists())
            result = runtime.compile_prompt(lane, allow_unreviewed=True)
        self.assertEqual(result["status"], "unreviewed_draft")
        attachments = runtime.read_json(lane / "delivery" / "attachments.json")
        self.assertFalse(attachments["submission_performed"])
        self.assertIsNone(attachments["generation_units"])
        self.assertTrue(all(item["platform_label"] is None for item in attachments["assets"]))
        self.assertEqual(len(attachments["assets"]), len(data["assets"]) + len(data["shots"]))
        prompt = (lane / "delivery" / "prompt.md").read_text(encoding="utf-8")
        self.assertNotIn("{{", prompt)
        delivery = runtime.read_json(lane / "delivery" / "delivery.json")
        self.assertEqual(delivery["prompt_sha256"], sha256_file(lane / "delivery" / "prompt.md"))
        self.assertEqual(delivery["counts"]["codepoints"], len(prompt))
        self.assertEqual(delivery["counts"]["utf16"], len(prompt.encode("utf-16-le")) // 2)

    def test_compile_limit_failure_does_not_write_delivery(self):
        lane = self.lane()
        data, manifest, report, binding = self.mock_media(lane)
        with mock.patch.object(runtime, "inspect", return_value={"binding": binding}), \
             mock.patch.object(runtime, "checked_backend", return_value=(lane, data, manifest, report)):
            with self.assertRaises(ContractError):
                runtime.compile_prompt(lane, allow_unreviewed=True, limit=10, reserve=2)
        self.assertFalse((lane / "delivery").exists())

    def final_text(self, lane, data, binding):
        edits_root = self.root / "authored-final-text"
        edits_root.mkdir(exist_ok=True)
        item = data["assets"][0]
        (edits_root / "prompt.md").write_text(
            "合成测试成稿😀\n\n## 输入包含\nD. 布局/其他输入：" + item["id"] + "\n",
            encoding="utf-8")
        record = {"schema": "product-tvc-final-text/v1", "binding": binding,
                  "semantic_review": "Synthetic text test only; actual media boundary is mocked, no playback claim.",
                  "units": [{"id": "U01", "start": 0, "end": data["duration_frames"],
                             "shot_ids": [s["id"] for s in data["shots"]], "entry_state": "test entry", "exit_state": "test exit",
                             "prompt_path": "prompt.md", "count_unit": "both", "limit": 1000, "reserve": 0,
                             "attachments": [{"id": item["id"], "sha256": item["sha256"], "upload": False,
                                              "platform_label": None, "purpose": "Synthetic structure reference"}]}]}
        path = edits_root / "edits.json"
        dump_json(path, record)
        return path, record

    def final_attachment(self, asset_id, sha256):
        return {"id": asset_id, "sha256": sha256, "upload": False,
                "platform_label": None, "purpose": "Synthetic explicit reference binding test"}

    def multi_unit_final_text(self, lane, data, binding):
        path, record = self.final_text(lane, data, binding)
        assets = {asset["id"]: asset for asset in data["assets"]}
        layout_images = {layout["id"]: layout["image_asset"] for layout in data["layouts"]}
        split = data["shots"][0]["end"]
        units = []
        for index, (start, end) in enumerate(((0, split), (split, data["duration_frames"])), 1):
            shots = [shot for shot in data["shots"] if start <= shot["start"] < end]
            image_ids = list(dict.fromkeys(layout_images[shot["layout"]] for shot in shots))
            clip_ids = ["PREVIS-" + shot["id"] for shot in shots]
            attachments = [self.final_attachment(asset_id, assets[asset_id]["sha256"]) for asset_id in image_ids]
            attachments += [self.final_attachment(clip_id, "a" * 64) for clip_id in clip_ids]
            prompt_name = f"unit-{index}.md"
            prompt = ("## 输入包含\nC. 白模预演视频：" + "、".join(clip_ids)
                      + "\nD. 布局/其他输入：" + "、".join(image_ids) + "\n\n"
                      + "\n".join("## " + shot["id"] + "\n保持当前镜头的合成代理动作。" for shot in shots))
            (path.parent / prompt_name).write_text(prompt, encoding="utf-8")
            units.append({"id": f"U{index:02d}", "start": start, "end": end,
                          "shot_ids": [shot["id"] for shot in shots],
                          "entry_state": "synthetic unit entry", "exit_state": "synthetic unit exit",
                          "prompt_path": prompt_name, "count_unit": "both", "limit": 3000,
                          "reserve": 0, "attachments": attachments})
        record["units"] = units
        dump_json(path, record)
        return path, record

    def test_finalize_valid_text_records_hash_counts_and_does_not_submit(self):
        lane = self.lane()
        data, manifest, report, binding = self.mock_media(lane)
        path, record = self.final_text(lane, data, binding)
        with mock.patch.object(runtime, "inspect", return_value={"binding": binding}), \
             mock.patch.object(runtime, "checked_backend", return_value=(lane, data, manifest, report)):
            result = runtime.finalize(lane, path)
        delivery = Path(result["delivery"])
        final = runtime.read_json(delivery / "delivery.json")
        self.assertFalse(final["submission_performed"])
        self.assertEqual(final["status"], "finalized_text_pending_playback")
        unit = final["units"][0]
        prompt = (delivery / unit["prompt"]).read_text(encoding="utf-8")
        self.assertEqual(unit["prompt_sha256"], sha256_file(delivery / unit["prompt"]))
        self.assertEqual(unit["counts"]["codepoints"], len(prompt))
        self.assertEqual(unit["counts"]["utf16"], len(prompt) + 1)

    def test_finalize_rejects_gaps_bad_shot_refs_hashes_labels_limits_and_path_escape(self):
        lane = self.lane()
        data, manifest, report, binding = self.mock_media(lane)
        path, original = self.final_text(lane, data, binding)
        cases = [(("units", 0, "start"), 1), (("units", 0, "end"), 179),
                 (("units", 0, "shot_ids"), ["S01"]),
                 (("units", 0, "attachments", 0, "id"), "missing"),
                 (("units", 0, "attachments", 0, "sha256"), "0" * 64),
                 (("units", 0, "attachments", 0, "platform_label"), "@image1"),
                 (("units", 0, "attachments", 0, "upload"), True),
                 (("units", 0, "limit"), 2), (("units", 0, "count_unit"), "tokens"),
                 (("units", 0, "prompt_path"), "../outside.md"), (("binding",), {})]
        with mock.patch.object(runtime, "inspect", return_value={"binding": binding}), \
             mock.patch.object(runtime, "checked_backend", return_value=(lane, data, manifest, report)):
            for fields, value in cases:
                with self.subTest(fields=fields):
                    record = copy.deepcopy(original)
                    replace(record, fields, value)
                    dump_json(path, record)
                    with self.assertRaises(ContractError):
                        runtime.finalize(lane, path)
                    self.assertFalse((lane / "finalized-delivery").exists())

    def test_finalize_rejects_clip_ids_in_body_when_only_full_video_is_attached(self):
        """Regression: nine explicit clip IDs cannot bind to an unmentioned full video."""
        lane = self.lane()
        data, manifest, report, binding = self.mock_media(lane)
        path, record = self.final_text(lane, data, binding)
        record["units"][0]["attachments"] = [self.final_attachment("PREVIS-FULL", "b" * 64)]
        prompt = "## 输入包含\nC. 白模预演视频：" + "、".join("PREVIS-" + shot["id"] for shot in data["shots"]) + "\n"
        (path.parent / "prompt.md").write_text(prompt, encoding="utf-8")
        dump_json(path, record)
        with mock.patch.object(runtime, "inspect", return_value={"binding": binding}), \
             mock.patch.object(runtime, "checked_backend", return_value=(lane, data, manifest, report)):
            with self.assertRaises(ContractError):
                runtime.finalize(lane, path)
        self.assertFalse((lane / "finalized-delivery").exists())

    def test_finalize_rejects_unmapped_explicit_reference_anywhere_in_unit_body(self):
        lane = self.lane()
        data, manifest, report, binding = self.mock_media(lane)
        path, record = self.final_text(lane, data, binding)
        declared = record["units"][0]["attachments"][0]["id"]
        cases = ["C. 白模预演视频：PREVIS-S01", "C. 白模预演视频：PREVIS-NO-SUCH-CLIP",
                 "## 后续动作\n主体的空间关系继续服从layout-B。", "C. 白模预演视频：PREVIS-S010"]
        with mock.patch.object(runtime, "inspect", return_value={"binding": binding}), \
             mock.patch.object(runtime, "checked_backend", return_value=(lane, data, manifest, report)):
            for extra in cases:
                with self.subTest(extra=extra):
                    prompt = "## 输入包含\nD. 布局/其他输入：" + declared + "\n" + extra + "\n"
                    (path.parent / "prompt.md").write_text(prompt, encoding="utf-8")
                    with self.assertRaises(ContractError):
                        runtime.finalize(lane, path)
                    self.assertFalse((lane / "finalized-delivery").exists())

    def test_finalize_rejects_attached_reference_not_mentioned_in_body(self):
        lane = self.lane()
        data, manifest, report, binding = self.mock_media(lane)
        path, original = self.final_text(lane, data, binding)
        with mock.patch.object(runtime, "inspect", return_value={"binding": binding}), \
             mock.patch.object(runtime, "checked_backend", return_value=(lane, data, manifest, report)):
            for extra_attachment in (False, True):
                with self.subTest(extra_attachment=extra_attachment):
                    record = copy.deepcopy(original)
                    prompt = "合成测试成稿，无显式附件引用。\n"
                    if extra_attachment:
                        prompt = "## 输入包含\nD. 布局/其他输入：" + data["assets"][0]["id"] + "\n"
                        record["units"][0]["attachments"].append(self.final_attachment("PREVIS-FULL", "b" * 64))
                    (path.parent / "prompt.md").write_text(prompt, encoding="utf-8")
                    dump_json(path, record)
                    with self.assertRaises(ContractError):
                        runtime.finalize(lane, path)
                    self.assertFalse((lane / "finalized-delivery").exists())

    def test_finalize_full_video_binding_accepts_body_without_stale_clip_ids(self):
        lane = self.lane()
        data, manifest, report, binding = self.mock_media(lane)
        path, record = self.final_text(lane, data, binding)
        record["units"][0]["attachments"] = [self.final_attachment("PREVIS-FULL", "b" * 64)]
        prompt = ("## 输入包含\nC. 白模预演视频：PREVIS-FULL\n\n"
                  + "\n".join("## " + shot["id"] + "\n保留合成代理动作。" for shot in data["shots"]))
        (path.parent / "prompt.md").write_text(prompt, encoding="utf-8")
        dump_json(path, record)
        with mock.patch.object(runtime, "inspect", return_value={"binding": binding}), \
             mock.patch.object(runtime, "checked_backend", return_value=(lane, data, manifest, report)):
            result = runtime.finalize(lane, path)
        delivery = runtime.read_json(Path(result["delivery"]) / "delivery.json")
        unit = delivery["units"][0]
        self.assertEqual(set(unit["prompt_attachment_ids"]), {"PREVIS-FULL"})
        self.assertEqual({item["id"] for item in unit["attachments"]}, {"PREVIS-FULL"})
        self.assertEqual((Path(result["delivery"]) / unit["prompt"]).read_text(encoding="utf-8"), prompt)
        self.assertFalse(delivery["submission_performed"])

    def test_finalize_multiple_units_bind_only_their_own_body_references(self):
        lane = self.lane()
        data, manifest, report, binding = self.mock_media(lane)
        path, record = self.multi_unit_final_text(lane, data, binding)
        with mock.patch.object(runtime, "inspect", return_value={"binding": binding}), \
             mock.patch.object(runtime, "checked_backend", return_value=(lane, data, manifest, report)):
            result = runtime.finalize(lane, path)
        delivery = runtime.read_json(Path(result["delivery"]) / "delivery.json")
        self.assertEqual(len(delivery["units"]), 2)
        for expected, actual in zip(record["units"], delivery["units"]):
            declared_ids = {item["id"] for item in expected["attachments"]}
            self.assertEqual(set(actual["prompt_attachment_ids"]), declared_ids)
            self.assertEqual({item["id"] for item in actual["attachments"]}, declared_ids)
            self.assertEqual(actual["shot_ids"], expected["shot_ids"])
            self.assertEqual((Path(result["delivery"]) / actual["prompt"]).read_text(encoding="utf-8"),
                             (path.parent / expected["prompt_path"]).read_text(encoding="utf-8"))
        first_ids = set(delivery["units"][0]["prompt_attachment_ids"])
        self.assertIn("PREVIS-S01", first_ids)
        self.assertNotIn("PREVIS-S02", first_ids)

    def test_finalize_rejects_using_another_units_attachment_to_resolve_a_reference(self):
        lane = self.lane()
        data, manifest, report, binding = self.mock_media(lane)
        path, record = self.multi_unit_final_text(lane, data, binding)
        first = record["units"][0]["attachments"]
        second = record["units"][1]["attachments"]
        first_clip = next(item for item in first if item["id"] == "PREVIS-S01")
        second_clip = next(item for item in second if item["id"] == "PREVIS-S02")
        first_clip["id"], second_clip["id"] = second_clip["id"], first_clip["id"]
        dump_json(path, record)
        # All needed IDs exist in the union, but each affected unit is wrong.
        self.assertTrue({"PREVIS-S01", "PREVIS-S02"}.issubset({item["id"] for unit in record["units"] for item in unit["attachments"]}))
        with mock.patch.object(runtime, "inspect", return_value={"binding": binding}), \
             mock.patch.object(runtime, "checked_backend", return_value=(lane, data, manifest, report)):
            with self.assertRaises(ContractError):
                runtime.finalize(lane, path)
        self.assertFalse((lane / "finalized-delivery").exists())

    def test_finalize_rejects_case_only_unit_id_collision_before_writing_files(self):
        lane = self.lane()
        data, manifest, report, binding = self.mock_media(lane)
        path, record = self.multi_unit_final_text(lane, data, binding)
        record["units"][1]["id"] = record["units"][0]["id"].lower()
        dump_json(path, record)
        with mock.patch.object(runtime, "inspect", return_value={"binding": binding}), \
             mock.patch.object(runtime, "checked_backend", return_value=(lane, data, manifest, report)):
            with self.assertRaises(ContractError):
                runtime.finalize(lane, path)
        self.assertFalse((lane / "finalized-delivery").exists())

    def test_finalize_verified_platform_aliases_resolve_to_canonical_attachment_ids(self):
        lane = self.lane()
        data, manifest, report, binding = self.mock_media(lane)
        path, record = self.final_text(lane, data, binding)
        record["provider"] = {"status": "verified", "name": "SYNTHETIC ENTRY", "entry": "test-only",
                              "checked_at": "2026-01-01", "evidence": "Synthetic record, no actual service used",
                              "max_seconds": 15, "max_images": 1, "supports_video_reference": True,
                              "label_syntax": "Synthetic @图片N / @视频N aliases"}
        image = record["units"][0]["attachments"][0]
        image.update(upload=True, platform_label="@图片1")
        video = self.final_attachment("PREVIS-FULL", "b" * 64)
        video.update(upload=True, platform_label="@视频1")
        record["units"][0]["attachments"].append(video)
        (path.parent / "prompt.md").write_text("## 输入包含\nC. 白模预演视频：@视频1\nD. 布局/其他输入：@图片1\n", encoding="utf-8")
        dump_json(path, record)
        with mock.patch.object(runtime, "inspect", return_value={"binding": binding}), \
             mock.patch.object(runtime, "checked_backend", return_value=(lane, data, manifest, report)):
            result = runtime.finalize(lane, path)
        delivery = runtime.read_json(Path(result["delivery"]) / "delivery.json")
        self.assertEqual(set(delivery["units"][0]["prompt_attachment_ids"]), {image["id"], "PREVIS-FULL"})
        self.assertFalse(delivery["submission_performed"])

    def test_finalize_rejects_labels_without_proposed_upload_or_colliding_with_neutral_ids(self):
        lane = self.lane()
        data, manifest, report, binding = self.mock_media(lane)
        path, original = self.final_text(lane, data, binding)
        original["provider"] = {"status": "verified", "name": "SYNTHETIC ENTRY", "entry": "test-only",
                                "checked_at": "2026-01-01", "evidence": "Synthetic record, no actual service used",
                                "max_seconds": 15, "max_images": 1, "supports_video_reference": True,
                                "label_syntax": "Synthetic @图片N alias"}
        with mock.patch.object(runtime, "inspect", return_value={"binding": binding}), \
             mock.patch.object(runtime, "checked_backend", return_value=(lane, data, manifest, report)):
            for upload, label in ((False, "@图片1"), (True, data["assets"][0]["id"])):
                with self.subTest(upload=upload, label=label):
                    record = copy.deepcopy(original)
                    record["units"][0]["attachments"][0].update(upload=upload, platform_label=label)
                    dump_json(path, record)
                    with self.assertRaises(ContractError):
                        runtime.finalize(lane, path)
                    self.assertFalse((lane / "finalized-delivery").exists())

    def test_finalize_rejects_unmapped_platform_tokens_in_body(self):
        lane = self.lane()
        data, manifest, report, binding = self.mock_media(lane)
        path, record = self.final_text(lane, data, binding)
        asset_id = record["units"][0]["attachments"][0]["id"]
        with mock.patch.object(runtime, "inspect", return_value={"binding": binding}), \
             mock.patch.object(runtime, "checked_backend", return_value=(lane, data, manifest, report)):
            for label in ("@图片1", "@视频2", "@音频1", "@image1", "@video2", "@audio1"):
                with self.subTest(label=label):
                    (path.parent / "prompt.md").write_text(
                        "## 输入包含\nD. 布局/其他输入：" + asset_id + "\n正文还要求引用" + label + "。\n",
                        encoding="utf-8")
                    with self.assertRaises(ContractError):
                        runtime.finalize(lane, path)
                    self.assertFalse((lane / "finalized-delivery").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
