#!/usr/bin/env python3
"""Append Shadow Observer events and propose rule candidates.

The observer is non-blocking by default. Use --strict only in package
verification or explicit certification diagnostics.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


FAILURE_CODES = {
    "route_misclass",
    "duration_defaulted",
    "escalation_trigger_missed",
    "reference_role_conflict",
    "insufficient_camera_variety",
    "weak_attention_order",
    "missing_depth_layers",
    "unmotivated_movement",
    "generic_premium_language",
    "scale_unproven",
    "photoreal_drift",
    "anime_manga_drift",
    "readable_text",
    "panel_separation_failure",
    "identity_drift",
    "product_identity_mismatch",
    "wrong_camera_angle",
    "repeated_centered_composition",
    "static_panel_dump",
    "missing_first_last_frame",
    "segment_continuity_break",
    "motion_not_motivated",
    "other",
}

SEVERITY_RANK = {
    "info": 0,
    "low": 1,
    "medium": 2,
    "high": 3,
    "severe": 4,
}

INFERENCE_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"route|project_type|misclass", re.I), "route_misclass"),
    (re.compile(r"duration|defaulted|segment", re.I), "duration_defaulted"),
    (re.compile(r"escalat|trigger", re.I), "escalation_trigger_missed"),
    (re.compile(r"reference.*conflict|conflicting_reference", re.I), "reference_role_conflict"),
    (re.compile(r"shot-size|camera-scale|camera-angle|distinct", re.I), "insufficient_camera_variety"),
    (re.compile(r"attention_order|first/second/third|attention", re.I), "weak_attention_order"),
    (re.compile(r"foreground|midground|background|depth", re.I), "missing_depth_layers"),
    (re.compile(r"movement|camera_movement|motivated", re.I), "unmotivated_movement"),
    (re.compile(r"premium|cinematic|beautiful|luxury|高级|电影感|奢华", re.I), "generic_premium_language"),
    (re.compile(r"scale_reference|scale proof|scale", re.I), "scale_unproven"),
    (re.compile(r"photoreal|photo-real|realistic", re.I), "photoreal_drift"),
    (re.compile(r"anime|manga|comic", re.I), "anime_manga_drift"),
    (re.compile(r"product.*(label|text|logo|mark|packag|blank|fake|wrong|generic|metal plate|badge|plaque|extra panel|emboss|relief|component)|label.*product|包装|标签|品牌文字|假品牌|空白瓶|错字|漏字|金属片|铭牌|徽章|浮雕|压印|产品.*(漂移|不一致|错字|漏字)", re.I), "product_identity_mismatch"),
    (re.compile(r"readable text|caption|unrelated text|shot number|subtitle", re.I), "readable_text"),
    (re.compile(r"panel separation|grid|border", re.I), "panel_separation_failure"),
    (re.compile(r"identity|product.*drift|character.*drift", re.I), "identity_drift"),
    (re.compile(r"wrong camera|camera angle", re.I), "wrong_camera_angle"),
    (re.compile(r"centered static|centered|static shots", re.I), "repeated_centered_composition"),
    (re.compile(r"static panel dump|paste.*panel", re.I), "static_panel_dump"),
    (re.compile(r"first-frame|last-frame|first frame|last frame", re.I), "missing_first_last_frame"),
    (re.compile(r"continuity break|segment continuity", re.I), "segment_continuity_break"),
    (re.compile(r"motion.*not|unmotivated motion|subject_motion|environment_motion", re.I), "motion_not_motivated"),
]

PROPOSAL_MAP = {
    "duration_defaulted": {
        "target_file": "scripts/route_project.py",
        "hypothesis": "The router is defaulting duration instead of extracting it from brief language.",
        "rule": "When duration or segment length appears in the brief, parse it before applying default timing.",
        "applies_when": "Brief contains time expressions or per-segment instructions.",
        "risk": "Over-parsing ambiguous poetic timing as hard duration.",
        "regression": "Input brief says 40s and 10s per segment; output must route to 2 storyboard sheets, 18 keyframes, and 4 video segments.",
    },
    "reference_role_conflict": {
        "target_file": "SKILL.md",
        "hypothesis": "Reference images have conflicting roles that were not escalated or resolved explicitly.",
        "rule": "When reference roles conflict on identity, location, or first-frame composition, state the conflict and escalate before shot planning.",
        "applies_when": "Two or more references imply incompatible product, person, location, or composition locks.",
        "risk": "Over-escalating normal mood-board variation.",
        "regression": "One image is product identity and another is negative reference; planner must not merge both as positive identity.",
    },
    "insufficient_camera_variety": {
        "target_file": "scripts/validate_shot_plan.py",
        "hypothesis": "The structure gate is catching camera variety failure often enough to deserve a stronger upstream planning rule.",
        "rule": "Before writing sheet prompts, rebalance any sheet with weak shot-size, angle, or movement variety.",
        "applies_when": "Validator reports missing distinct shot-size, camera-angle, or movement states.",
        "risk": "Variety for its own sake can damage a deliberately restrained visual language.",
        "regression": "A 9-shot sheet must not pass with repeated centered medium shots and only two camera angles.",
    },
    "weak_attention_order": {
        "target_file": "references/shot_spec_template.md",
        "hypothesis": "Attention choreography is being written as prose rather than a concrete first/second/third visual read.",
        "rule": "Every attention_order must name the first, second, and third visual read and how it prepares the next cut.",
        "applies_when": "Shot plan contains attention_order without explicit read sequence.",
        "risk": "Overly mechanical attention notes can reduce useful ambiguity in surreal scenes.",
        "regression": "A shot with attention_order='product feels premium' must be rejected as non-specific.",
    },
    "missing_depth_layers": {
        "target_file": "references/shot_spec_template.md",
        "hypothesis": "Shots are passing with weak foreground, midground, background, or depth strategy decisions.",
        "rule": "Each non-macro shot must define foreground, midground, background, and why that depth structure matters.",
        "applies_when": "Shot is not an extreme macro and lacks explicit depth-layer design.",
        "risk": "Flat graphic compositions can be valid when intentionally designed.",
        "regression": "A wide product-world shot with empty foreground/midground/background must be rejected.",
    },
    "generic_premium_language": {
        "target_file": "SKILL.md",
        "hypothesis": "The workflow is still using abstract prestige language instead of visible decisions.",
        "rule": "Replace premium/cinematic/beautiful claims with camera height, scale, material, action, and cut logic.",
        "applies_when": "Shot purpose, prompt, or QC relies on abstract prestige words.",
        "risk": "Some brand briefs use premium as a category label; the ban applies to final shot decisions, not intake language.",
        "regression": "A shot purpose that only says 'make the product premium and cinematic' must fail.",
    },
    "repeated_centered_composition": {
        "target_file": "scripts/validate_shot_plan.py",
        "hypothesis": "The plan is overusing centered static compositions despite variety requirements.",
        "rule": "Reject three consecutive centered static shots unless the plan declares a deliberate graphic repetition pattern.",
        "applies_when": "Three adjacent shots are centered and static.",
        "risk": "Some packshot endings intentionally use stable centered composition.",
        "regression": "Three consecutive centered static mid shots must fail without an explicit repetition rationale.",
    },
    "readable_text": {
        "target_file": "references/shot_spec_template.md",
        "hypothesis": "Storyboard image prompts are allowing unrelated text-like marks that violate the storyboard cleanliness constraint.",
        "rule": "Storyboard sheets must reject captions, subtitles, shot numbers, handwritten notes, fake labels, and unrelated readable text while preserving user-provided product packaging marks.",
        "applies_when": "Post-image QC detects non-product readable text or text-like panel labels.",
        "risk": "A broad no-text rule can incorrectly erase real product packaging identity.",
        "regression": "Generated storyboard sheet with shot numbers or unrelated labels must be regenerated; a real supplied product label must not be treated as contamination.",
    },
    "product_identity_mismatch": {
        "target_file": "SKILL.md",
        "hypothesis": "The product identity lock is missing or not being enforced strongly enough in storyboard planning, storyboard prompting, generated sheets, or video prompts.",
        "rule": "When a user product is visible, preserve the locked package silhouette, label layout, supplied product text, logo/mark, embossed or relief marks, color blocks, real physical components, materials, and cap/pump/closure; reject blank packaging, misspelled or missing copy, fake brands, invented claims, changed layouts, generic product substitutes, and non-reference additions such as metal plates, badges, plaques, extra panels, or wrong hardware.",
        "applies_when": "A shot plan, storyboard prompt, generated sheet, or video segment blanks, misspells, omits, invents, or adds visible product packaging facts that are not in the user-provided reference.",
        "risk": "Tiny microtext may be impossible in rough storyboard or video scale; preserve label geometry and every readable primary supplied mark rather than inventing details.",
        "regression": "A user-provided bottle labeled LUMA / HYDRATING SERUM / 30 ml with no front metal plate must not become a blank cosmetic bottle, a different fake brand, misspelled text, or a bottle with an added metal badge/plaque in a full-visible video segment.",
    },
    "panel_separation_failure": {
        "target_file": "references/workflow_contract.md",
        "hypothesis": "The image prompt is not enforcing a readable dynamic N-panel storyboard grid strongly enough.",
        "rule": "Every storyboard sheet prompt must require clear separation for its declared grid layout and reject merged, missing, or extra panels.",
        "applies_when": "Generated sheet has missing, merged, or ambiguous panels.",
        "risk": "Some storyboard styles use loose gutters; separation still must be readable.",
        "regression": "A generated sheet whose visible panel count or layout does not match panels_per_sheet/grid_layouts must be regenerated.",
    },
    "identity_drift": {
        "target_file": "SKILL.md",
        "hypothesis": "Product or character identity locks are not strong enough across sheet generation.",
        "rule": "Product and character identity references must be converted into continuity locks before prompting.",
        "applies_when": "Generated or planned shots change product shape, person identity, or required prop structure.",
        "risk": "A rough or stylized storyboard finish can simplify identity; the lock concerns structure, not finish.",
        "regression": "A product with a cylindrical pump cannot become a flat jar across panels.",
    },
    "static_panel_dump": {
        "target_file": "SKILL.md",
        "hypothesis": "Video prompts are copying storyboard panels instead of describing motion over time.",
        "rule": "Each video segment prompt must define first frame, last frame, camera motion, subject motion, environment motion, and continuity lock.",
        "applies_when": "Google omni prompt reads as a list of static panel descriptions.",
        "risk": "Some lockoff shots are valid, but the segment still needs temporal change.",
        "regression": "A 10s segment that only lists panels SH_001-SH_006 must fail.",
    },
    "missing_first_last_frame": {
        "target_file": "references/video_segments.schema.json",
        "hypothesis": "Video segment prompts are missing temporal boundaries.",
        "rule": "Each video segment must include concrete first_frame and last_frame fields.",
        "applies_when": "Segment prompt lacks first-frame or last-frame description.",
        "risk": "A montage segment may have several internal endpoints; still define segment boundary frames.",
        "regression": "SEG_01 without first_frame or last_frame must be invalid.",
    },
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def event_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"evt_{stamp}_{uuid.uuid4().hex[:8]}"


def observer_dir(run_dir: Path) -> Path:
    out = run_dir / "_observer"
    out.mkdir(parents=True, exist_ok=True)
    return out


def events_path(run_dir: Path) -> Path:
    return observer_dir(run_dir) / "events.jsonl"


def read_text(path: Path, max_chars: int = 1200) -> str:
    text = path.read_text(encoding="utf-8", errors="replace")
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_chars]


def parse_codes(value: str | None) -> list[str]:
    if not value:
        return []
    codes = []
    for raw in value.split(","):
        code = raw.strip()
        if code in FAILURE_CODES and code not in codes:
            codes.append(code)
    return codes


def infer_codes(message: str) -> list[str]:
    found = []
    for pattern, code in INFERENCE_RULES:
        if pattern.search(message) and code not in found:
            found.append(code)
    return found or ["other"]


def write_event(run_dir: Path, event: dict) -> Path:
    path = events_path(run_dir)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
    return path


def make_event(
    *,
    run_dir: Path,
    stage: str,
    source_artifact: str,
    event_type: str,
    severity: str,
    failure_codes: list[str],
    evidence: str,
    production_mode: str,
    observer_mode: str,
    related_shots: list[str] | None = None,
    related_images: list[str] | None = None,
    prompt_excerpt: str = "",
    suggested_fix: str = "",
    candidate_rule_id: str = "",
) -> dict:
    event = {
        "event_id": event_id(),
        "run_id": run_dir.name,
        "created_at": utc_now(),
        "production_mode": production_mode,
        "observer_mode": observer_mode,
        "stage": stage,
        "source_artifact": source_artifact,
        "event_type": event_type,
        "severity": severity,
        "failure_codes": failure_codes,
        "evidence": evidence,
        "related_shots": related_shots or [],
        "related_images": related_images or [],
    }
    if prompt_excerpt:
        event["prompt_excerpt"] = prompt_excerpt
    if suggested_fix:
        event["suggested_fix"] = suggested_fix
    if candidate_rule_id:
        event["candidate_rule_id"] = candidate_rule_id
    return event


def cmd_append(args: argparse.Namespace) -> int:
    if args.observer_mode == "off":
        return 0

    run_dir = args.run_dir.resolve()
    payload_excerpt = ""
    if args.payload:
        payload_path = Path(args.payload)
        if payload_path.exists():
            payload_excerpt = read_text(payload_path)
        else:
            payload_excerpt = str(args.payload)[:1200]

    evidence = args.evidence or payload_excerpt or f"{args.stage} event recorded"
    codes = parse_codes(args.failure_codes)
    event = make_event(
        run_dir=run_dir,
        stage=args.stage,
        source_artifact=args.artifact or args.payload or "",
        event_type=args.event_type,
        severity=args.severity,
        failure_codes=codes,
        evidence=evidence,
        production_mode=args.production_mode,
        observer_mode=args.observer_mode,
        related_shots=parse_list(args.related_shots),
        related_images=parse_list(args.related_images),
        prompt_excerpt=args.prompt_excerpt or "",
        suggested_fix=args.suggested_fix or "",
    )
    print(write_event(run_dir, event))
    return 0


def parse_list(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def cmd_ingest_validator(args: argparse.Namespace) -> int:
    if args.observer_mode == "off":
        return 0

    run_dir = args.run_dir.resolve()
    data = load_json(args.validator_result)
    errors = data.get("errors", []) or []
    warnings = data.get("warnings", []) or []

    if not errors and not warnings:
        event = make_event(
            run_dir=run_dir,
            stage="structure_gate",
            source_artifact=str(args.validator_result),
            event_type="validator_pass",
            severity="info",
            failure_codes=[],
            evidence="Shot-plan validator passed with no errors or warnings.",
            production_mode=args.production_mode,
            observer_mode=args.observer_mode,
        )
        print(write_event(run_dir, event))
        return 0

    output_path = None
    for message in errors:
        event = make_event(
            run_dir=run_dir,
            stage="structure_gate",
            source_artifact=str(args.validator_result),
            event_type="validator_error",
            severity="high",
            failure_codes=infer_codes(str(message)),
            evidence=str(message),
            production_mode=args.production_mode,
            observer_mode=args.observer_mode,
            related_shots=extract_shot_ids(str(message)),
        )
        output_path = write_event(run_dir, event)

    for message in warnings:
        event = make_event(
            run_dir=run_dir,
            stage="structure_gate",
            source_artifact=str(args.validator_result),
            event_type="validator_warning",
            severity="medium",
            failure_codes=infer_codes(str(message)),
            evidence=str(message),
            production_mode=args.production_mode,
            observer_mode=args.observer_mode,
            related_shots=extract_shot_ids(str(message)),
        )
        output_path = write_event(run_dir, event)

    if output_path:
        print(output_path)
    return 0


def extract_shot_ids(message: str) -> list[str]:
    ids = re.findall(r"\bSH[_-]?\d{1,4}\b", message, flags=re.I)
    return sorted({item.upper().replace("-", "_") for item in ids})


def load_events(path: Path) -> list[dict]:
    events = []
    if not path.exists():
        return events
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        events.append(json.loads(line))
    return events


def candidate_id(code: str, event_ids: list[str]) -> str:
    digest = hashlib.sha1(("|".join([code, *event_ids])).encode("utf-8")).hexdigest()[:10]
    return f"rc_{code}_{digest}"


def proposal_for(code: str) -> dict:
    default = {
        "target_file": "other",
        "hypothesis": f"Repeated observer evidence suggests a missing rule for {code}.",
        "rule": f"Add a testable rule that prevents {code}.",
        "applies_when": f"Observer evidence includes {code}.",
        "risk": "The pattern may be local to one brief rather than a general skill weakness.",
        "regression": f"Create a fixture that reproduces {code} and fails before the rule is added.",
    }
    return PROPOSAL_MAP.get(code, default)


def build_candidate_result(events: list[dict], events_label: str, min_count: int) -> dict:
    by_code: dict[str, list[dict]] = defaultdict(list)
    for event in events:
        for code in event.get("failure_codes", []) or []:
            by_code[code].append(event)

    candidates = []
    code_counts = Counter({code: len(items) for code, items in by_code.items()})
    for code, items in sorted(by_code.items()):
        if code == "other" and len(items) < min_count:
            continue
        has_severe = any(SEVERITY_RANK.get(str(item.get("severity", "info")), 0) >= SEVERITY_RANK["severe"] for item in items)
        if len(items) < min_count and not has_severe:
            continue
        event_ids = [str(item.get("event_id", "")) for item in items if item.get("event_id")]
        proposal = proposal_for(code)
        candidates.append({
            "candidate_rule_id": candidate_id(code, event_ids),
            "created_from_events": event_ids,
            "failure_code": code,
            "hypothesis": proposal["hypothesis"],
            "proposed_rule_text": proposal["rule"],
            "target_file": proposal["target_file"],
            "applies_when": proposal["applies_when"],
            "counterexample_risk": proposal["risk"],
            "regression_case": proposal["regression"],
            "promotion_status": "proposed",
        })

    return {
        "generated_at": utc_now(),
        "events_path": events_label,
        "event_count": len(events),
        "failure_code_counts": dict(sorted(code_counts.items())),
        "candidate_rules": candidates,
        "note": "Candidate rules are proposals only. They require explicit skill-improvement work or SSOT acceptance before becoming durable rules.",
    }


def write_result(result: dict, out: Path | None) -> None:
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
    else:
        print(text, end="")


def cmd_propose_rules(args: argparse.Namespace) -> int:
    events = load_events(args.events)
    result = build_candidate_result(events, str(args.events), args.min_count)
    write_result(result, args.out)
    return 0


def cmd_aggregate_runs(args: argparse.Namespace) -> int:
    root = args.root.resolve()
    event_files = sorted(root.rglob("_observer/events.jsonl"))
    events: list[dict] = []
    for path in event_files:
        for event in load_events(path):
            event.setdefault("source_events_file", str(path))
            events.append(event)

    result = build_candidate_result(
        events,
        f"{root}/**/_observer/events.jsonl",
        args.min_count,
    )
    result["source_event_file_count"] = len(event_files)
    result["source_event_files"] = [str(path) for path in event_files]
    write_result(result, args.out)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true", help="return non-zero on observer errors")
    subparsers = parser.add_subparsers(dest="command", required=True)

    append = subparsers.add_parser("append")
    append.add_argument("--run-dir", type=Path, required=True)
    append.add_argument("--stage", required=True, choices=[
        "intake",
        "route",
        "shot_plan",
        "structure_gate",
        "storyboard_prompt",
        "post_image_qc",
        "video_prompt",
        "final_qc",
        "skill_packaging",
        "other",
    ])
    append.add_argument("--artifact", default="")
    append.add_argument("--payload")
    append.add_argument("--event-type", default="artifact_recorded", choices=[
        "artifact_recorded",
        "validator_pass",
        "validator_warning",
        "validator_error",
        "route_issue",
        "prompt_issue",
        "image_qc_issue",
        "video_prompt_issue",
        "user_correction",
        "candidate_rule_generated",
        "other",
    ])
    append.add_argument("--severity", default="info", choices=["info", "low", "medium", "high", "severe"])
    append.add_argument("--failure-codes", default="")
    append.add_argument("--evidence", default="")
    append.add_argument("--related-shots", default="")
    append.add_argument("--related-images", default="")
    append.add_argument("--prompt-excerpt", default="")
    append.add_argument("--suggested-fix", default="")
    append.add_argument("--production-mode", default="unknown", choices=["standard_fast", "rush", "premium_pitch", "certification", "unknown"])
    append.add_argument("--observer-mode", default="auto", choices=["auto", "off", "full"])
    append.set_defaults(func=cmd_append)

    ingest = subparsers.add_parser("ingest-validator")
    ingest.add_argument("--run-dir", type=Path, required=True)
    ingest.add_argument("--validator-result", type=Path, required=True)
    ingest.add_argument("--production-mode", default="unknown", choices=["standard_fast", "rush", "premium_pitch", "certification", "unknown"])
    ingest.add_argument("--observer-mode", default="auto", choices=["auto", "off", "full"])
    ingest.set_defaults(func=cmd_ingest_validator)

    propose = subparsers.add_parser("propose-rules")
    propose.add_argument("--events", type=Path, required=True)
    propose.add_argument("--out", type=Path)
    propose.add_argument("--min-count", type=int, default=3)
    propose.set_defaults(func=cmd_propose_rules)

    aggregate = subparsers.add_parser("aggregate-runs")
    aggregate.add_argument("--root", type=Path, required=True)
    aggregate.add_argument("--out", type=Path)
    aggregate.add_argument("--min-count", type=int, default=3)
    aggregate.set_defaults(func=cmd_aggregate_runs)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.func(args)
    except Exception as exc:
        print(f"observer warning: {exc}", file=sys.stderr)
        return 1 if getattr(args, "strict", False) else 0


if __name__ == "__main__":
    raise SystemExit(main())
