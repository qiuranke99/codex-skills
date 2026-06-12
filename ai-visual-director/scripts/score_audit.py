#!/usr/bin/env python3
"""Score an AI Visual Director audit JSON and return readiness status."""

from __future__ import annotations

import json
import sys
from pathlib import Path


WEIGHTS = {
    "brief_alignment": 10,
    "reference_role_accuracy": 10,
    "route_decision_logic": 10,
    "dramatic_arc": 10,
    "shot_language_variety": 15,
    "continuity_control": 10,
    "storyboard_prompt_quality": 10,
    "video_prompt_motion_design": 10,
    "visual_qc": 10,
    "commercial_risk_control": 5,
}

CRITICAL = {
    "brief_alignment",
    "reference_role_accuracy",
    "dramatic_arc",
    "shot_language_variety",
    "continuity_control",
    "video_prompt_motion_design",
}


def load(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def score(audit: dict) -> dict:
    blockers = list(audit.get("blockers") or [])
    dimensions = audit.get("dimensions") or {}
    errors: list[str] = []
    warnings: list[str] = []

    weighted = 0.0
    total_weight = sum(WEIGHTS.values())
    dimension_results = {}

    for key, weight in WEIGHTS.items():
        item = dimensions.get(key)
        if not item:
            errors.append(f"missing dimension: {key}")
            raw = 0.0
            evidence = ""
        else:
            raw = float(item.get("score", 0))
            evidence = str(item.get("evidence", "")).strip()
            if not evidence:
                warnings.append(f"{key}: missing evidence")
            if item.get("revision_required"):
                warnings.append(f"{key}: marked revision_required")
        raw = max(0.0, min(5.0, raw))
        weighted += (raw / 5.0) * weight
        dimension_results[key] = {
            "score": raw,
            "weighted_points": round((raw / 5.0) * weight, 2),
            "weight": weight,
            "critical": key in CRITICAL,
        }

    total = round((weighted / total_weight) * 100, 2)
    critical_low = [
        key for key, item in dimension_results.items()
        if item["critical"] and item["score"] < 4.0
    ]
    critical_world_low = [
        key for key, item in dimension_results.items()
        if item["critical"] and item["score"] < 4.5
    ]

    review_round = int(audit.get("review_round") or 0)
    independent_review_count = int(audit.get("independent_review_count") or 0)
    adversarial_review_done = bool(audit.get("adversarial_review_done"))

    if errors or blockers or total < 75 or any(dimension_results.get(k, {}).get("score", 0) < 3 for k in CRITICAL):
        status = "fail"
    elif total < 85 or critical_low or warnings:
        status = "revise"
    elif total >= 92 and not critical_world_low and review_round >= 2 and independent_review_count >= 2 and adversarial_review_done:
        status = "world_class_candidate"
    else:
        status = "commercial_candidate"

    return {
        "ok": status in {"commercial_candidate", "world_class_candidate"},
        "status": status,
        "total_score": total,
        "blockers": blockers,
        "errors": errors,
        "warnings": warnings,
        "critical_below_commercial": critical_low,
        "critical_below_world_class": critical_world_low,
        "dimension_results": dimension_results,
        "requirements": {
            "commercial_candidate": "score >= 85, no blockers, no errors, all critical dimensions >= 4.0, no unresolved serious warnings",
            "world_class_candidate": "score >= 92, no blockers, all critical dimensions >= 4.5, review_round >= 2, independent_review_count >= 2, adversarial_review_done = true",
        },
    }


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: score_audit.py <audit.json>", file=sys.stderr)
        return 2
    result = score(load(sys.argv[1]))
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
