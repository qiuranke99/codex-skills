import csv
import hashlib
import http.server
import json
import tempfile
import threading
import unittest
from pathlib import Path


class _Handler(http.server.BaseHTTPRequestHandler):
    image_bytes = b"\x89PNG\r\n\x1a\n" + b"reference-image"

    def do_HEAD(self):
        self._serve(send_body=False)

    def do_GET(self):
        self._serve(send_body=True)

    def log_message(self, format, *args):
        return

    def _serve(self, send_body):
        if self.path == "/ok":
            body = b"ok"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if send_body:
                self.wfile.write(body)
        elif self.path == "/missing":
            self.send_response(404)
            self.end_headers()
        elif self.path == "/redirect":
            self.send_response(302)
            self.send_header("Location", "/ok")
            self.end_headers()
        elif self.path == "/image.png":
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(self.image_bytes)))
            self.end_headers()
            if send_body:
                self.wfile.write(self.image_bytes)
        elif self.path == "/soft404":
            body = b"<html><title>Not found</title><body>This content is no longer available.</body></html>"
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if send_body:
                self.wfile.write(body)
        elif self.path == "/login":
            body = b"<html><body>Please log in to continue viewing this post.</body></html>"
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if send_body:
                self.wfile.write(body)
        elif self.path == "/page-with-image":
            body = b"""
            <html>
              <head><meta property="og:image" content="/image.png"></head>
              <body><img src="/image.png" width="1200" height="900" alt="reference"></body>
            </html>
            """
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if send_body:
                self.wfile.write(body)
        else:
            self.send_response(500)
            self.end_headers()


class ReferenceToolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_url_checker_reports_reachable_redirect_and_404(self):
        from scripts.verify_urls import check_url

        ok = check_url(f"{self.base_url}/ok", timeout=2)
        missing = check_url(f"{self.base_url}/missing", timeout=2)
        redirected = check_url(f"{self.base_url}/redirect", timeout=2)

        self.assertEqual(ok["state"], "ok")
        self.assertEqual(missing["state"], "not_found")
        self.assertEqual(redirected["state"], "redirected")
        self.assertEqual(redirected["status_code"], 200)
        self.assertTrue(redirected["final_url"].endswith("/ok"))

    def test_url_checker_detects_soft_404_and_login_wall(self):
        from scripts.verify_urls import check_url

        soft404 = check_url(f"{self.base_url}/soft404", timeout=2)
        login = check_url(f"{self.base_url}/login", timeout=2)

        self.assertEqual(soft404["state"], "soft_404")
        self.assertEqual(login["state"], "login_required")

    def test_image_downloader_writes_file_and_manifest(self):
        from scripts.download_reference_images import download_records

        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "pack"
            records = [
                {
                    "rank": "1",
                    "title": "Local eyeliner texture",
                    "source_url": f"{self.base_url}/ok",
                    "image_url": f"{self.base_url}/image.png",
                    "visual_mechanism": "macro material texture",
                }
            ]

            manifest = download_records(records, output_dir, timeout=2)

            self.assertEqual(len(manifest), 1)
            item = manifest[0]
            self.assertEqual(item["download_status"], "downloaded")
            image_path = output_dir / item["download_path"]
            sidecar_path = output_dir / item["sidecar_path"]
            self.assertTrue(image_path.exists())
            self.assertTrue(sidecar_path.exists())
            self.assertEqual(
                item["sha256"], hashlib.sha256(_Handler.image_bytes).hexdigest()
            )

            csv_path = output_dir / "manifest.csv"
            json_path = output_dir / "manifest.json"
            self.assertTrue(csv_path.exists())
            self.assertTrue(json_path.exists())

            with csv_path.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            with json_path.open(encoding="utf-8") as handle:
                payload = json.load(handle)

            self.assertEqual(rows[0]["source_url"], f"{self.base_url}/ok")
            self.assertEqual(payload[0]["image_url"], f"{self.base_url}/image.png")

    def test_extract_image_candidates_reads_page_metadata(self):
        from scripts.extract_image_candidates import extract_page_image_candidates

        candidates = extract_page_image_candidates(
            {
                "rank": "1",
                "title": "Portfolio page",
                "source_url": f"{self.base_url}/page-with-image",
            },
            timeout=2,
        )

        self.assertTrue(candidates)
        self.assertEqual(candidates[0]["source_url"], f"{self.base_url}/page-with-image")
        self.assertEqual(candidates[0]["image_url"], f"{self.base_url}/image.png")
        self.assertEqual(candidates[0]["capture_method"], "og_image")

    def test_pack_builder_extracts_and_downloads_from_source_pages(self):
        from scripts.build_image_reference_pack import build_pack

        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "auto-pack"
            records = [
                {
                    "rank": "1",
                    "title": "Auto pack source",
                    "source_url": f"{self.base_url}/page-with-image",
                    "visual_mechanism": "controlled silver reflection",
                }
            ]

            result = build_pack(records, output_dir, timeout=2, min_width=0)

            self.assertTrue((output_dir / "sources.jsonl").exists())
            self.assertTrue((output_dir / "image_candidates.jsonl").exists())
            self.assertTrue((output_dir / "manifest.json").exists())
            self.assertEqual(result["downloaded_count"], 1)
            self.assertEqual(result["manifest"][0]["download_status"], "downloaded")
            self.assertTrue((output_dir / result["manifest"][0]["download_path"]).exists())

    def test_pack_builder_records_skipped_sources_when_no_image_is_found(self):
        from scripts.build_image_reference_pack import build_pack

        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "empty-pack"
            records = [
                {
                    "rank": "1",
                    "title": "No image source",
                    "source_url": f"{self.base_url}/ok",
                    "visual_mechanism": "source has no usable image",
                }
            ]

            result = build_pack(records, output_dir, timeout=2, min_width=0)

            self.assertEqual(result["candidate_count"], 1)
            self.assertEqual(result["downloaded_count"], 0)
            self.assertEqual(result["skipped_count"], 1)
            self.assertEqual(result["manifest"][0]["download_status"], "skipped_no_direct_image_url")
            self.assertTrue((output_dir / "manifest.json").exists())


if __name__ == "__main__":
    unittest.main()
