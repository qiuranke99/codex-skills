#!/usr/bin/env python3
"""Portable tests for legacy Word/table source extraction."""

from __future__ import annotations

import tempfile
import zipfile
from pathlib import Path
from types import SimpleNamespace

from extract_source_document import analyze_extraction, build_report, extract_source


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "legacy_shot_table_extracted.txt"


def main() -> int:
    fixture_text = FIXTURE.read_text(encoding="utf-8")
    analysis = analyze_extraction(fixture_text)
    if analysis["detected_shot_numbers"] != ["01", "02", "03"]:
        raise AssertionError(f"shot order lost: {analysis}")
    if any("2031-4" in token for token in analysis["detected_time_tokens"]):
        raise AssertionError(f"calendar date was misclassified as shot timing: {analysis}")

    calls: list[list[str]] = []

    def fake_textutil(command: list[str], **_: object) -> SimpleNamespace:
        calls.append(command)
        legacy = fixture_text.replace("\t", "\x07").encode("utf-8")
        return SimpleNamespace(returncode=0, stdout=legacy, stderr=b"")

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        legacy_doc = root / "rough-script.doc"
        legacy_doc.write_bytes(b"OLE fixture placeholder")
        text, method, _ = extract_source(legacy_doc, fake_textutil)
        if method != "textutil_stdout" or "\x07" in text or "\t" not in text:
            raise AssertionError("legacy Word table normalization failed")
        if calls != [["textutil", "-convert", "txt", "-stdout", str(legacy_doc)]]:
            raise AssertionError(f"unexpected converter invocation: {calls}")
        report = build_report(legacy_doc, method, "decoded_output", text)
        if report["detected_shot_numbers"] != ["01", "02", "03"]:
            raise AssertionError(f"legacy report lost order: {report}")

        docx = root / "rough-script.docx"
        xml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            '<w:body><w:p><w:r><w:t>01</w:t></w:r><w:tab/><w:r><w:t>0-2s</w:t></w:r></w:p>'
            '<w:p><w:r><w:t>镜头内容</w:t></w:r></w:p></w:body></w:document>'
        )
        with zipfile.ZipFile(docx, "w") as archive:
            archive.writestr("word/document.xml", xml)

        def missing_textutil(*_: object, **__: object) -> object:
            raise FileNotFoundError("textutil unavailable")

        docx_text, docx_method, _ = extract_source(docx, missing_textutil)
        if docx_method != "docx_xml_fallback" or "01\t0-2s" not in docx_text:
            raise AssertionError("DOCX XML fallback failed")

    print("PASS: legacy .doc routing, table order, provenance report, and DOCX fallback")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
