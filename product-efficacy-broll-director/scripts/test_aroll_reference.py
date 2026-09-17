#!/usr/bin/env python3
"""Real synthetic-media regression; no customer files, network or paid services."""
from __future__ import annotations

import json
import math
import subprocess
import tempfile
import unittest
from pathlib import Path

import aroll_reference as ar


class BoundsTests(unittest.TestCase):
    def test_finite_time_and_eof(self):
        for at in [-1, math.nan, math.inf, -math.inf, 2, 3]:
            with self.subTest(at=at), self.assertRaises(ar.MediaError):
                ar.validate_time(at, 2)
        ar.validate_time(0, 2)
        ar.validate_time(1.99, 2)

    def test_sample_coverage_and_count(self):
        values = ar.sample_times(15, 12)
        self.assertEqual(len(values), 12)
        self.assertTrue(0 < values[0] < 1)
        self.assertTrue(14 < values[-1] < 15)
        self.assertEqual(values, sorted(set(values)))
        for count in [0, 1, 49]:
            with self.assertRaises(ar.MediaError):
                ar.sample_times(15, count)

    def test_hdr_marks(self):
        for stream in [{"color_transfer": "smpte2084"}, {"color_transfer": "arib-std-b67"},
                       {"side_data_list": [{"side_data_type": "DOVI configuration record"}]}]:
            self.assertTrue(ar.hdr_marked(stream))
        self.assertFalse(ar.hdr_marked({"color_transfer": "bt709"}))
        self.assertFalse(ar.hdr_marked({}))


class MediaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Required real integration; missing tools are a failure, never a skipped pass.
        ar.executable("ffmpeg")
        ar.executable("ffprobe")
        cls.temp = tempfile.TemporaryDirectory(prefix="broll-media-test-")
        cls.root = Path(cls.temp.name)
        cls.video = cls.root / "中文 样本.mkv"
        ar.run([ar.executable("ffmpeg"), "-v", "error", "-nostdin", "-n",
                "-f", "lavfi", "-i", "color=c=red:s=48x80:r=8:d=1",
                "-f", "lavfi", "-i", "color=c=blue:s=48x80:r=8:d=1",
                "-filter_complex", "[0:v][1:v]concat=n=2:v=1:a=0[v]", "-map", "[v]",
                "-c:v", "mpeg4", "-q:v", "2", str(cls.video)])
        cls.original_hash = ar.sha256(cls.video)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        self.out = self.root / self._testMethodName
        self.out.mkdir()

    def tearDown(self):
        self.assertEqual(ar.sha256(self.video), self.original_hash)

    def test_probe_and_real_color_at_two_times(self):
        media = ar.read_media(self.video)
        self.assertAlmostEqual(media["duration_seconds"], 2, places=2)
        self.assertEqual(media["source_sha256"], self.original_hash)
        for at, channel in [(0.25, 0), (1.25, 2)]:
            dest = self.out / f"frame-{channel}.png"
            result = ar.extract_frame(self.video, at, dest)
            self.assertEqual(result["frame"]["width_height"], [48, 80])
            self.assertEqual(result["frame"]["sha256"], ar.sha256(dest))
            decoded = subprocess.run([ar.executable("ffmpeg"), "-v", "error", "-i", str(dest),
                                      "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                                     check=True, capture_output=True, timeout=15).stdout
            pixel = decoded[:3]
            self.assertGreater(pixel[channel], 200)
            self.assertTrue(all(pixel[c] < 30 for c in range(3) if c != channel))
            saved = json.loads(dest.with_suffix(".json").read_text(encoding="utf-8"))
            self.assertEqual(saved["source_sha256"], self.original_hash)

    def test_inspect_samples_and_overview(self):
        result = ar.inspect_video(self.video, self.out / "inspection", 4)
        self.assertEqual(len(result["samples"]), 4)
        self.assertEqual([s["requested_seconds"] for s in result["samples"]], [.25, .75, 1.25, 1.75])
        self.assertTrue((self.out / "inspection" / "overview.jpg").stat().st_size > 100)
        self.assertEqual(result["samples"][0]["width_height"][0], 320)

    def test_refuse_existing_output_and_sidecar(self):
        dest = self.out / "reference.png"
        dest.write_bytes(b"user-data")
        with self.assertRaises(ar.MediaError):
            ar.extract_frame(self.video, .25, dest)
        self.assertEqual(dest.read_bytes(), b"user-data")
        dest2 = self.out / "reference-2.png"
        dest2.with_suffix(".json").write_text("existing", encoding="utf-8")
        with self.assertRaises(ar.MediaError):
            ar.extract_frame(self.video, .25, dest2)
        self.assertFalse(dest2.exists())
        with self.assertRaises(ar.MediaError):
            ar.inspect_video(self.video, self.out, 4)

    def test_invalid_time_creates_no_output(self):
        for at in [-1, math.nan, math.inf, 2.0]:
            with self.assertRaises(ar.MediaError):
                ar.extract_frame(self.video, at, self.out / "invalid.png")
        self.assertEqual(list(self.out.iterdir()), [])

    def test_audio_only_and_invalid_file(self):
        audio = self.out / "audio.wav"
        ar.run([ar.executable("ffmpeg"), "-v", "error", "-f", "lavfi", "-i",
                "sine=duration=0.1", str(audio)])
        with self.assertRaises(ar.MediaError):
            ar.read_media(audio)
        junk = self.out / "junk.mp4"
        junk.write_text("not a video", encoding="utf-8")
        with self.assertRaises(ar.MediaError):
            ar.read_media(junk)

    def test_hdr_source_refused_before_writing(self):
        hdr = self.out / "tagged-hdr.mkv"
        ar.run([ar.executable("ffmpeg"), "-v", "error", "-i", str(self.video),
                "-vf", "setparams=color_trc=smpte2084:color_primaries=bt2020:colorspace=bt2020nc",
                "-c:v", "ffv1", str(hdr)])
        with self.assertRaisesRegex(ar.MediaError, "HDR detected"):
            ar.extract_frame(hdr, .25, self.out / "wrong-look.png")
        self.assertFalse((self.out / "wrong-look.png").exists())

    def test_anamorphic_display_ratio(self):
        anamorphic = self.out / "sar.mkv"
        ar.run([ar.executable("ffmpeg"), "-v", "error", "-i", str(self.video),
                "-vf", "setsar=2", "-c:v", "ffv1", str(anamorphic)])
        result = ar.extract_frame(anamorphic, .25, self.out / "square-pixels.png")
        self.assertEqual(result["frame"]["width_height"], [96, 80])

    def test_rotation_display_orientation(self):
        rotated = self.out / "rotated.mp4"
        ffmpeg = ar.executable("ffmpeg")
        # New FFmpeg uses an input display-matrix option; older builds use metadata.
        help_text = ar.run([ffmpeg, "-hide_banner", "-h", "full"])
        if "-display_rotation" in help_text:
            ar.run([ffmpeg, "-v", "error", "-display_rotation", "90", "-i", str(self.video),
                    "-c:v", "copy", str(rotated)])
        else:
            ar.run([ffmpeg, "-v", "error", "-i", str(self.video),
                    "-c:v", "copy", "-metadata:s:v:0", "rotate=90", str(rotated)])
        result = ar.extract_frame(rotated, .25, self.out / "oriented.png")
        self.assertEqual(result["frame"]["width_height"], [80, 48])


if __name__ == "__main__":
    unittest.main(verbosity=2)
