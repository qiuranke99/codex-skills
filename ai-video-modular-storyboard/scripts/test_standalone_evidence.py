#!/usr/bin/env python3
"""Exercise caller-pinned standalone sources and immutable replacement bases."""
from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from test_contract import create_package, dependency, seal, write_json, write_png
from validate_storyboard_package import sha256_file, validate_package

HERE = Path(__file__).resolve().parent


def make_standalone(case: Path, *, text: bool = True, replacement: bool = False, stage: str = "structure_draft"):
    package = case / "storyboard"
    manifest = create_package(package, 3, replacement_count=1 if replacement else 0,
                              project_root=case, intrinsic_text=text, stage=stage)
    canon_path = case / "00_project_canon/PROJECT_CANON_MANIFEST.json"
    canon = json.loads(canon_path.read_text(encoding="utf-8"))
    evidence = {"schema_version": "storyboard-source-evidence.v1", "sources": [], "replacement_bases": []}
    for entry in canon["active_artifacts"]:
        if entry["owner_skill"] == "ai-video-modular-storyboard":
            continue
        evidence["sources"].append({
            "artifact_ref": {key: entry[key] for key in ("artifact_id", "owner_skill", "version", "sha256")},
            "artifact_type": entry["artifact_type"], "primary_path": entry["locator"],
            "primary_file_sha256": entry["file_sha256"], "record_path": entry["artifact_record_locator"],
            "record_file_sha256": entry["artifact_record_file_sha256"],
        })
    for transaction in manifest["transactions"]:
        evidence["replacement_bases"].append({"transaction_id": transaction["transaction_id"],
            "artifact_ref": copy.deepcopy(transaction["base_manifest_ref"]),
            "file_sha256": transaction["base_manifest_file_sha256"]})
    path = case / "caller-source-evidence.json"
    write_json(path, evidence)
    # Remove only test-created registry/receipt: standalone validation cannot use them.
    canon_path.unlink()
    (package / "00_manifest/MANIFEST_UPDATE_RECEIPT.json").unlink()
    return package, path, sha256_file(path), case


def check(case, expected: str | None = None):
    package, evidence, digest, input_root = case
    errors = validate_package(package, source_evidence_path=evidence,
                              source_evidence_sha256=digest, input_root=input_root)
    if expected is None and errors:
        raise AssertionError(f"standalone valid input rejected: {errors}")
    if expected is not None and not any(expected in error for error in errors):
        raise AssertionError(f"expected {expected!r}, got {errors}")


def edit_evidence(case, change, *, repin=False):
    package, path, digest, input_root = case
    value = json.loads(path.read_text(encoding="utf-8"))
    change(value)
    write_json(path, value)
    return package, path, sha256_file(path) if repin else digest, input_root


def edit_manifest(package: Path, change):
    path = package / "00_manifest/STORYBOARD_MANIFEST.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    change(value)
    seal(value)
    write_json(path, value)
    write_json(package / "04_qa/validation_report.json", {"status": "passed", "validated_manifest_sha256": value["sha256"]})


def main() -> int:
    tests = 0
    with tempfile.TemporaryDirectory(prefix="storyboard-source-evidence-") as temp:
        root = Path(temp)
        for text, replacement in ((True, False), (False, True), (True, True)):
            case = make_standalone(root / f"valid-{text}-{replacement}", text=text, replacement=replacement)
            check(case)
            tests += 1
        for replacement in (False, True):
            check(make_standalone(root / f"final-{replacement}", replacement=replacement, stage="look_applied_final"))
            tests += 1
        plain = make_standalone(root / "ordinary", text=False)
        errors = validate_package(plain[0])
        if errors:
            raise AssertionError(f"ordinary no-text/no-replacement compatibility failed: {errors}")
        tests += 1
        cli = make_standalone(root / "cli")
        result = subprocess.run([sys.executable, "-B", str(HERE / "validate_storyboard_package.py"),
            str(cli[0]), "--source-evidence", str(cli[1]), "--source-evidence-sha256", cli[2],
            "--input-root", str(cli[3])], capture_output=True, text=True)
        if result.returncode != 0:
            raise AssertionError(f"standalone CLI failed: {result.stdout} {result.stderr}")
        tests += 1

        missing = make_standalone(root / "missing-digest")
        check((missing[0], missing[1], None, missing[3]), "caller-pinned SHA-256")
        tests += 1
        badhash = make_standalone(root / "missing-source-hash")
        check(edit_evidence(badhash, lambda data: data["sources"][1].pop("primary_file_sha256"), repin=True), "exact source byte locks")
        tests += 1
        changed = make_standalone(root / "changed-primary")
        write_png(changed[3] / "authorities/packaging/PACKAGING_LABEL_SOURCE.png", rgb=(1, 2, 3))
        check(changed, "primary file hash mismatch")
        tests += 1
        forged = make_standalone(root / "forged-label")
        def forge_label(data):
            frame = data["frames"][0]
            fake = dependency("INVENTED", "invented", "1.0.0", "9" * 64)
            frame["content_cleanliness"]["intrinsic_text_source_refs"] = [fake]
            frame["dependencies"][-1] = fake
            seal(frame)
        edit_manifest(forged[0], forge_label)
        check(forged, "intrinsic text source absent from caller-pinned evidence")
        tests += 1
        category = make_standalone(root / "wrong-category")
        check(edit_evidence(category, lambda data: data["sources"][1].__setitem__("artifact_type", "soundtrack"), repin=True), "not a product/packaging/label/scene authority")
        tests += 1
        url = make_standalone(root / "url-source")
        check(edit_evidence(url, lambda data: data["sources"][1].__setitem__("primary_path", "https://example.invalid/logo.png"), repin=True), "primary file hash mismatch")
        tests += 1
        mismatch = make_standalone(root / "record-identity")
        record_path = mismatch[3] / "authorities/packaging/PACKAGING_LABEL_SOURCE.json"
        record = json.loads(record_path.read_text(encoding="utf-8"))
        record["artifact_id"] = "FORGED_ID"
        seal(record)
        write_json(record_path, record)
        check(mismatch, "source record identity/approval differs")
        tests += 1

        rewritten = make_standalone(root / "rewrite-base", replacement=True)
        def rewrite_base(manifest):
            transaction = manifest["transactions"][0]
            base_path = rewritten[0] / transaction["base_manifest_path"]
            base = json.loads(base_path.read_text(encoding="utf-8"))
            base["project_id"] = "REWRITTEN_AFTER_PIN"
            seal(base)
            write_json(base_path, base)
            original = transaction["base_manifest_ref"]
            replacement_ref = {key: base[key] for key in original}
            transaction["dependencies"] = [replacement_ref if item == original else item for item in transaction["dependencies"]]
            transaction["base_manifest_ref"] = replacement_ref
            transaction["base_manifest_file_sha256"] = sha256_file(base_path)
            seal(transaction)
        edit_manifest(rewritten[0], rewrite_base)
        check(rewritten, "pre-transaction manifest differs from caller-pinned base")
        tests += 1
        changed_pin = make_standalone(root / "rewrite-evidence", replacement=True)
        check(edit_evidence(changed_pin, lambda data: data["replacement_bases"][0].__setitem__("file_sha256", "0" * 64)), "source evidence differs from caller-pinned SHA-256")
        tests += 1
        missing_base = make_standalone(root / "missing-base", replacement=True)
        check(edit_evidence(missing_base, lambda data: data.__setitem__("replacement_bases", []), repin=True), "pre-transaction manifest differs from caller-pinned base")
        tests += 1
        unchanged = make_standalone(root / "unrequested-frame", replacement=True)
        def alter_unrequested(manifest):
            frame = manifest["frames"][1]
            frame["version"] = "8.0.0"
            seal(frame)
        edit_manifest(unchanged[0], alter_unrequested)
        check(unchanged, "unaffected shot SHT_002 artifact record changed")
        tests += 1
        upstream = make_standalone(root / "upstream-tamper", replacement=True)
        shot_path = upstream[3] / "authorities/SHOT_CONTRACT.json"
        shot = json.loads(shot_path.read_text(encoding="utf-8"))
        shot["global_directing_prompt_full"] += " CHANGED"
        seal(shot)
        write_json(shot_path, shot)
        check(upstream, "primary file hash mismatch")
        tests += 1
        internal = make_standalone(root / "inside-output")
        inside = internal[0] / "caller-evidence.json"
        inside.write_bytes(internal[1].read_bytes())
        check((internal[0], inside, internal[2], internal[3]), "outside the mutable storyboard package")
        tests += 1
    print(f"PASS: {tests} standalone source-evidence/immutable-base cases, including CLI and ordinary-path compatibility")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
