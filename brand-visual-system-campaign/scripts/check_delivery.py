#!/usr/bin/env python3
"""Read-only checks for delivery coverage, file versions and review records.

Standard library only. This is not a visual evaluator, identity authenticator,
approval service or proof of independent cognition.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import struct
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

SHA = re.compile(r"[0-9a-f]{64}")
IDENT = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]*")
KINDS = {"image", "video", "document", "source"}
METHODS = {
    "image": {"visual"},
    "video": {"playback_full"},
    "document": {"rendered_pages"},
    "source": {"opened_source"},
}


class CheckError(ValueError):
    pass


def need(condition: bool, message: str) -> None:
    if not condition:
        raise CheckError(message)


def nonblank(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        need(key not in result, f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path: Path) -> dict[str, Any]:
    need(path.stat().st_size <= 8 * 1024 * 1024, f"JSON record too large: {path.name}")
    data = json.loads(path.read_text(encoding="utf-8-sig"), object_pairs_hook=unique_object)
    need(isinstance(data, dict), f"JSON root must be an object: {path.name}")
    return data


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def contained_path(root: Path, value: Any) -> Path:
    need(nonblank(value), "file path must be a non-empty string")
    # Packages remain portable. Reject parent traversal, drive paths and URLs.
    value = value.replace("\\", "/")
    need(not value.startswith("/") and ":" not in value, "use a project-relative path")
    need(".." not in value.split("/"), "parent traversal is not permitted")
    path = (root / value).resolve(strict=True)
    need(path.is_relative_to(root), "resolved path escapes the project root")
    need(path.is_file(), f"expected file: {value}")
    need(path.stat().st_size > 0, f"empty file: {value}")
    return path


def bound_file(root: Path, ref: Any) -> Path:
    need(isinstance(ref, dict), "file reference must be an object")
    expected = ref.get("sha256")
    need(isinstance(expected, str) and SHA.fullmatch(expected) is not None,
         "file reference requires a lowercase SHA256")
    path = contained_path(root, ref.get("path"))
    need(sha256(path) == expected, f"file hash changed: {ref.get('path')}")
    return path


def records(value: Any, label: str) -> list[dict[str, Any]]:
    need(isinstance(value, list) and bool(value), f"{label} must be a non-empty list")
    need(all(isinstance(item, dict) for item in value), f"{label} items must be objects")
    ids = [item.get("id") for item in value]
    need(all(isinstance(item, str) and IDENT.fullmatch(item) for item in ids),
         f"{label} requires safe non-empty IDs")
    need(len(set(ids)) == len(ids), f"duplicate IDs in {label}")
    return value


def timestamp(value: Any) -> datetime:
    need(nonblank(value), "review timestamp is required")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    need(parsed.tzinfo is not None, "review timestamp requires a timezone")
    return parsed


def read_contract(root: Path, contract_path: Path) -> dict[str, Any]:
    contract = load_json(contract_path)
    need(contract.get("schema_version") == "brand-delivery-contract.v1",
         "unsupported contract schema")
    need(nonblank(contract.get("project")), "project name is required")
    inputs = records(contract.get("inputs"), "inputs")
    requirements = records(contract.get("requirements"), "requirements")
    for flag in ("independent_review_required", "user_review_required"):
        need(type(contract.get(flag)) is bool, f"{flag} must be boolean")
    input_map = {item["id"]: item for item in inputs}
    for item in inputs:
        need(item.get("status") in {"provided", "approved", "rejected"}, "invalid input status")
        need(nonblank(item.get("role")), "input role is required")
        bound_file(root, item)
    for requirement in requirements:
        kind = requirement.get("kind")
        need(kind in KINDS, "unsupported deliverable kind")
        need(nonblank(requirement.get("purpose")), "deliverable purpose is required")
        refs = requirement.get("source_input_ids")
        need(isinstance(refs, list) and refs and all(isinstance(x, str) for x in refs),
             "source_input_ids must be a non-empty string list")
        need(len(set(refs)) == len(refs), "duplicate source_input_ids")
        need(all(x in input_map for x in refs), "unknown source input")
        selected = [input_map[x] for x in refs]
        need(all(x["status"] != "rejected" for x in selected), "rejected input is active")
        need(any(x["role"] == "brief" for x in selected), "original brief input is required")
        need(type(requirement.get("contains_text")) is bool, "contains_text must be boolean")
        checks = requirement.get("required_checks")
        need(isinstance(checks, list) and checks and all(nonblank(x) for x in checks),
             "required_checks must be a non-empty string list")
        need(len(set(checks)) == len(checks), "duplicate required_checks")
        mandatory = {"editability"} if kind == "source" else {"brand", "craft", "composition"}
        if any(x["role"] == "product" for x in selected) and kind != "source":
            mandatory.add("product")
        if requirement["contains_text"]:
            mandatory.add("copy")
        if kind == "video":
            mandatory.add("motion")
        need(mandatory <= set(checks), f"missing mandatory checks: {sorted(mandatory-set(checks))}")
        spec = requirement.get("spec")
        need(isinstance(spec, dict) and bool(spec), "an actual output spec is required")
        for key, value in spec.items():
            need(nonblank(key) and (nonblank(value) or type(value) in {int, float, bool}),
                 "spec values must be finite numbers, booleans or non-empty strings")
            if type(value) in {int, float}:
                need(math.isfinite(value) and value > 0, "numeric specs must be positive and finite")
        if kind in {"image", "video"}:
            need(all(type(spec.get(key)) is int and spec[key] > 0 for key in ("width", "height")),
                 "image/video requires integer width and height")
        if kind == "video":
            need(type(spec.get("duration")) in {int, float} and spec["duration"] > 0,
                 "video requires duration in seconds")
    return contract


def inputs_digest(contract: dict[str, Any], requirement: dict[str, Any]) -> str:
    selected = {x["id"]: x for x in contract["inputs"]}
    payload = {
        "project": contract["project"],
        "requirement": requirement,
        "inputs": [selected[x] for x in sorted(requirement["source_input_ids"])],
        "independent_review_required": contract["independent_review_required"],
    }
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def check_evidence(root: Path, evidence: Any) -> None:
    need(isinstance(evidence, list) and evidence, "actual review evidence is required")
    for item in evidence:
        bound_file(root, item)


def check_results(review: dict[str, Any], required: list[str], *, passing: bool) -> None:
    checks = review.get("checks")
    need(isinstance(checks, dict), "review checks must be an object")
    need(set(required) <= set(checks), "review omitted a required check")
    for name, value in checks.items():
        need(isinstance(value, dict), f"check {name} must be an object")
        need(value.get("result") in {"pass", "fail", "unverified"}, f"invalid result: {name}")
        need(nonblank(value.get("observation")), f"concrete observation missing: {name}")
        if passing:
            need(value["result"] == "pass", f"unresolved check: {name}={value['result']}")
    limits = review.get("limitations")
    need(isinstance(limits, list) and all(nonblank(x) for x in limits), "invalid limitations")
    if passing:
        need(not limits, "review has unresolved limitations")


def check_review(root: Path, review: dict[str, Any], output: dict[str, Any],
                 requirement: dict[str, Any], digest: str, independent_required: bool) -> None:
    need(review.get("kind") in {"self", "independent"}, "review kind must be self or independent")
    need(nonblank(review.get("reviewer")), "actual reviewer identity is required")
    need(review.get("artifact_sha256") == output["file"]["sha256"], "review targets stale output")
    need(review.get("inputs_digest") == digest, "review targets stale inputs or requirements")
    need(review.get("method") in METHODS[requirement["kind"]], "review method mismatches media")
    final_time = timestamp(review.get("recorded_at"))
    check_results(review, requirement["required_checks"], passing=True)
    check_evidence(root, review.get("evidence"))
    if independent_required:
        need(review["kind"] == "independent", "independent review is still required")
    if review["kind"] == "independent":
        need(review["reviewer"] != output["creator"], "creator cannot claim independent review")
        first = load_json(bound_file(root, review.get("first_review")))
        need(first.get("kind") == "first_independent_review", "missing first independent review")
        need(first.get("reviewer") == review["reviewer"], "first reviewer identity changed")
        need(first.get("participated_in_production") is False, "reviewer participated in production")
        need(first.get("exposure") == "none", "first reviewer had prior explanation exposure")
        need(first.get("artifact_sha256") == output["file"]["sha256"], "first review targets stale output")
        need(first.get("inputs_digest") == digest, "first review targets stale inputs")
        need(timestamp(first.get("recorded_at")) < final_time, "first review must precede comparison")
        check_results(first, requirement["required_checks"], passing=False)
        check_evidence(root, first.get("evidence"))
        for name in requirement["required_checks"]:
            if first["checks"][name]["result"] != review["checks"][name]["result"]:
                need(nonblank(review["checks"][name].get("change_reason")),
                     f"changed review result has no reason: {name}")


def png_header_size(path: Path) -> tuple[int, int] | None:
    if path.suffix.lower() != ".png":
        return None
    with path.open("rb") as handle:
        header = handle.read(24)
    need(len(header) == 24 and header[:8] == b"\x89PNG\r\n\x1a\n"
         and header[8:16] == b"\x00\x00\x00\rIHDR", "invalid PNG header")
    return struct.unpack(">II", header[16:24])


def check_technical(root: Path, output: dict[str, Any], requirement: dict[str, Any], path: Path) -> None:
    probe = load_json(bound_file(root, output.get("technical")))
    need(probe.get("artifact_sha256") == output["file"]["sha256"], "technical probe targets stale output")
    need(probe.get("passed") is True and nonblank(probe.get("method")), "technical probe did not pass")
    observed = probe.get("observed")
    need(isinstance(observed, dict), "technical probe has no observed properties")
    for key, expected in requirement["spec"].items():
        actual = observed.get(key)
        if type(expected) in {int, float}:
            need(type(actual) in {int, float} and math.isfinite(actual), f"invalid observed {key}")
            # Tolerance is numerical serialization only, not a creative/duration allowance.
            need(math.isclose(actual, expected, rel_tol=1e-9, abs_tol=1e-9), f"spec mismatch: {key}")
        else:
            need(type(actual) is type(expected) and actual == expected, f"spec mismatch: {key}")
    dimensions = png_header_size(path)
    if dimensions is not None:
        need(dimensions == (requirement["spec"].get("width"), requirement["spec"].get("height")),
             "actual PNG dimensions mismatch")


def check_delivery(root: Path, contract_path: Path, manifest_path: Path) -> dict[str, Any]:
    root = root.resolve(strict=True)
    errors: list[dict[str, str]] = []
    checked: list[str] = []
    acceptance = "unknown"
    try:
        need(root.is_dir(), "project root must be a directory")
        need(contract_path.resolve().is_relative_to(root), "contract must be inside project")
        need(manifest_path.resolve().is_relative_to(root), "manifest must be inside project")
        contract = read_contract(root, contract_path)
        manifest = load_json(manifest_path)
        need(manifest.get("schema_version") == "brand-delivery-manifest.v1", "unsupported manifest schema")
        need(bound_file(root, manifest.get("contract")) == contract_path.resolve(), "wrong contract reference")
        outputs = records(manifest.get("outputs"), "outputs")
        required = {item["id"]: item for item in contract["requirements"]}
        provided = {item["id"]: item for item in outputs}
        need(set(provided) == set(required),
             f"coverage mismatch; missing={sorted(set(required)-set(provided))}; extra={sorted(set(provided)-set(required))}")
        artifacts: dict[str, str] = {}
        for output_id, output in provided.items():
            try:
                requirement = required[output_id]
                need(nonblank(output.get("creator")), "actual creator identity is required")
                path = bound_file(root, output.get("file"))
                digest = inputs_digest(contract, requirement)
                need(output.get("inputs_digest") == digest, "output is bound to stale inputs or requirements")
                artifact = output["file"]["sha256"]
                if artifact in artifacts:
                    previous = required[artifacts[artifact]]
                    need(requirement.get("allow_shared_artifact") is True
                         and previous.get("allow_shared_artifact") is True,
                         "same file bytes reused for distinct required outputs without explicit permission")
                artifacts[artifact] = output_id
                check_technical(root, output, requirement, path)
                review = load_json(bound_file(root, output.get("review")))
                check_review(root, review, output, requirement, digest, contract["independent_review_required"])
                checked.append(output_id)
            except (CheckError, OSError, ValueError, TypeError, KeyError) as exc:
                errors.append({"output_id": output_id, "error": str(exc)})
        user = manifest.get("user_acceptance")
        need(isinstance(user, dict), "user_acceptance record is required")
        acceptance = user.get("status")
        need(acceptance in {"not_requested", "pending", "accepted"}, "invalid user acceptance status")
        if contract["user_review_required"]:
            need(acceptance != "not_requested", "required user review was discarded")
        if acceptance == "accepted":
            record = load_json(bound_file(root, user.get("record")))
            need(nonblank(record.get("approved_by")) and nonblank(record.get("source")),
                 "user acceptance requires actual source and approver")
            need(record.get("contract_sha256") == sha256(contract_path), "user acceptance targets stale contract")
            need(record.get("accepted_outputs") == {x["id"]: x["file"]["sha256"] for x in outputs},
                 "user acceptance does not cover these exact outputs")
    except (CheckError, OSError, ValueError, TypeError, KeyError) as exc:
        errors.append({"output_id": "", "error": str(exc)})
    return {
        "schema_version": "brand-delivery-check.v1",
        "status": "check_failed" if errors else "delivery_files_and_records_valid",
        "checked_outputs": checked,
        "user_acceptance": acceptance,
        "errors": errors,
        "limits": [
            "Checks file coverage, hashes, specifications and recorded observations; does not view pixels or play media.",
            "Non-PNG metadata comes from the attached technical probe. PNG dimensions are rechecked from the header, not decoded.",
            "Does not authenticate people, user messages, actual reading order, independence or market effectiveness.",
            "This report alone is not visual approval or user acceptance.",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    hash_parser = sub.add_parser("hash", help="print the SHA256 of one explicitly named local file")
    hash_parser.add_argument("file", type=Path)
    for name in ("check", "inputs-digest"):
        command = sub.add_parser(name)
        command.add_argument("--root", required=True, type=Path)
        command.add_argument("--contract", default="contract.json")
        if name == "check":
            command.add_argument("--manifest", default="delivery.json")
        else:
            command.add_argument("--output-id", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "hash":
            need(args.file.is_file(), "file does not exist")
            print(json.dumps({"sha256": sha256(args.file)}, ensure_ascii=False))
            return 0
        root = args.root.resolve(strict=True)
        contract_path = contained_path(root, args.contract)
        if args.command == "inputs-digest":
            contract = read_contract(root, contract_path)
            matching = [x for x in contract["requirements"] if x["id"] == args.output_id]
            need(len(matching) == 1, "unknown output ID")
            result = {"output_id": args.output_id, "inputs_digest": inputs_digest(contract, matching[0])}
        else:
            result = check_delivery(root, contract_path, contained_path(root, args.manifest))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if result.get("status") == "check_failed" else 0
    except (CheckError, OSError, ValueError, TypeError, KeyError) as exc:
        print(json.dumps({"status": "check_failed", "errors": [{"error": str(exc)}]}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())
