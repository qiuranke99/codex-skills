#!/usr/bin/env python3
"""Detect exact, identity, variant, and perceptual duplicates in candidates."""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from _contract_utils import ContractError, get_path, read_records, same_artifact, write_json


TRACKING_KEYS = {
    "fbclid",
    "gclid",
    "igshid",
    "mc_cid",
    "mc_eid",
    "ref",
    "source",
}


def normalize_url(raw: Any) -> str:
    if not isinstance(raw, str) or not raw.strip():
        return ""
    value = raw.strip()
    parts = urlsplit(value)
    scheme = parts.scheme.lower() or "https"
    host = (parts.hostname or "").lower()
    port = parts.port
    netloc = host
    if port and not ((scheme == "http" and port == 80) or (scheme == "https" and port == 443)):
        netloc = f"{host}:{port}"
    path = parts.path.rstrip("/") or "/"
    filtered = []
    for key, item in parse_qsl(parts.query, keep_blank_values=True):
        lower = key.lower()
        if lower.startswith("utm_") or lower in TRACKING_KEYS:
            continue
        filtered.append((key, item))
    filtered.sort()
    return urlunsplit((scheme, netloc, path, urlencode(filtered, doseq=True), ""))


def _hex_distance(left: str, right: str) -> int | None:
    try:
        if len(left) != len(right) or not left:
            return None
        return (int(left, 16) ^ int(right, 16)).bit_count()
    except ValueError:
        return None


def _validated_hash(value: Any, field_name: str, digits: int) -> str:
    if value in (None, ""):
        return ""
    if not isinstance(value, str) or re.fullmatch(rf"[0-9a-fA-F]{{{digits}}}", value) is None:
        raise ContractError(f"{field_name} must be exactly {digits} hexadecimal characters")
    return value.lower()


class UnionFind:
    def __init__(self, values: list[str]) -> None:
        self.parent = {value: value for value in values}

    def find(self, value: str) -> str:
        parent = self.parent[value]
        if parent != value:
            self.parent[value] = self.find(parent)
        return self.parent[value]

    def union(self, left: str, right: str) -> None:
        root_left = self.find(left)
        root_right = self.find(right)
        if root_left != root_right:
            self.parent[root_right] = root_left


def candidate_id(candidate: dict[str, Any]) -> str:
    value = candidate.get("candidate_id", candidate.get("id"))
    if not isinstance(value, str) or not value:
        raise ContractError("candidate is missing candidate_id")
    return value


def _candidate_signals(candidate: dict[str, Any]) -> dict[str, str]:
    stable_media_id = get_path(
        candidate,
        "object.stable_id",
        "stable_media_id",
        "identity.platform_id",
        "media_identity.stable_id",
        default="",
    )
    source_id = get_path(candidate, "source.source_id", "source_id", default="")
    exact_hash = get_path(
        candidate,
        "dedup.fingerprint.exact_or_manifest_sha256",
        "dedup.content_hash",
        "media_hash",
        "fingerprints.exact_sha256",
        "fingerprints.media_sha256",
        default="",
    )
    perceptual_hash = get_path(
        candidate,
        "dedup.fingerprint.perceptual_hash",
        "dedup.perceptual_hash",
        "perceptual_hash",
        "fingerprints.perceptual_hash",
        "fingerprints.phash",
        default="",
    )
    variant_group = get_path(
        candidate,
        "dedup.near_duplicate_group_id",
        "variant_group_id",
        "identity.variant_group_id",
        default="",
    )
    work_id = get_path(candidate, "work_id", "identity.work_id", default="")
    canonical = normalize_url(
        get_path(candidate, "object.canonical_url", "canonical_url", "source_url", default="")
    )
    return {
        "canonical_url": canonical,
        "stable_key": f"{source_id}:{stable_media_id}" if stable_media_id else "",
        "exact_hash": _validated_hash(exact_hash, "exact/content hash", 64),
        "perceptual_hash": _validated_hash(perceptual_hash, "perceptual hash", 16),
        "variant_group": str(variant_group or ""),
        "work_id": str(work_id or ""),
    }


def find_duplicate_groups(
    candidates: list[dict[str, Any]], phash_distance: int = 6
) -> list[dict[str, Any]]:
    if isinstance(phash_distance, bool) or not isinstance(phash_distance, int) or not 0 <= phash_distance <= 64:
        raise ContractError("phash_distance must be an integer from 0 through 64")
    ids = [candidate_id(candidate) for candidate in candidates]
    if len(ids) != len(set(ids)):
        raise ContractError("candidate_id values must be unique before deduplication")
    union = UnionFind(ids)
    reasons: dict[frozenset[str], set[str]] = defaultdict(set)
    signals = {candidate_id(item): _candidate_signals(item) for item in candidates}

    indexed: dict[tuple[str, str], str] = {}
    for cid in ids:
        for signal_name in ("canonical_url", "stable_key", "exact_hash", "work_id", "variant_group"):
            signal = signals[cid][signal_name]
            if not signal:
                continue
            key = (signal_name, signal)
            if key in indexed:
                other = indexed[key]
                union.union(cid, other)
                reasons[frozenset((cid, other))].add(signal_name)
            else:
                indexed[key] = cid

    for index, left in enumerate(ids):
        left_hash = signals[left]["perceptual_hash"]
        if not left_hash:
            continue
        left_modality = get_path(candidates[index], "modality", "source_media_type", default="")
        for right_index in range(index + 1, len(ids)):
            right = ids[right_index]
            right_modality = get_path(candidates[right_index], "modality", "source_media_type", default="")
            if left_modality and right_modality and left_modality != right_modality:
                continue
            distance = _hex_distance(left_hash, signals[right]["perceptual_hash"])
            if distance is not None and distance <= phash_distance:
                union.union(left, right)
                reasons[frozenset((left, right))].add(f"perceptual_hash_distance={distance}")

    grouped: dict[str, list[str]] = defaultdict(list)
    for cid in ids:
        grouped[union.find(cid)].append(cid)

    result: list[dict[str, Any]] = []
    for members in grouped.values():
        if len(members) < 2:
            continue
        group_reasons: set[str] = set()
        for pair, pair_reasons in reasons.items():
            if pair.issubset(members):
                group_reasons.update(pair_reasons)
        group_key = "|".join(sorted(members))
        result.append(
            {
                "duplicate_group_id": "dup-" + hashlib.sha256(group_key.encode()).hexdigest()[:12],
                "candidate_ids": sorted(members),
                "reasons": sorted(group_reasons),
                "kept_candidate_id": sorted(members)[0],
            }
        )
    return sorted(result, key=lambda item: item["candidate_ids"])


def build_report(candidates: list[dict[str, Any]], phash_distance: int = 6) -> dict[str, Any]:
    groups = find_duplicate_groups(candidates, phash_distance=phash_distance)
    duplicate_ids = {cid for group in groups for cid in group["candidate_ids"]}
    return {
        "candidate_count": len(candidates),
        "duplicate_group_count": len(groups),
        "duplicate_candidate_count": len(duplicate_ids),
        "phash_distance_threshold": phash_distance,
        "duplicate_groups": groups,
        "pass": not groups,
        "note": (
            "Perceptual matches are review signals. A run validator may accept an explicitly "
            "documented version-comparison exemption; this detector never silently suppresses one."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", required=True, help="candidate JSON/JSONL")
    parser.add_argument("--output", required=True, help="dedup report JSON")
    parser.add_argument("--phash-distance", type=int, default=6)
    parser.add_argument("--fail-on-duplicates", action="store_true")
    args = parser.parse_args(argv)
    try:
        if same_artifact(args.candidates, args.output):
            raise ContractError("output must not overwrite the candidate ledger")
        candidates = read_records(args.candidates)
        report = build_report(candidates, phash_distance=args.phash_distance)
        write_json(args.output, report)
    except ContractError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if args.fail_on_duplicates and not report["pass"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
