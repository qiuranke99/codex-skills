#!/usr/bin/env python3
"""Validate mandatory role-agent orchestration for ai-visual-director runs."""

from __future__ import annotations

import json
import sys
from pathlib import Path


REQUIRED_AGENTS = {
    "creative_director_agent",
    "director_agent",
    "screenwriter_agent",
    "art_director_agent",
    "google_omni_prompt_expert_agent",
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def has_text(value: object) -> bool:
    if isinstance(value, list):
        return any(str(item).strip() for item in value)
    return bool(str(value).strip())


def pointer_get(payload: object, pointer: str) -> object:
    if pointer in {"", "/"}:
        return payload
    current = payload
    for raw_part in pointer.strip("/").split("/"):
        part = raw_part.replace("~1", "/").replace("~0", "~")
        if isinstance(current, dict):
            if part not in current:
                raise KeyError(part)
            current = current[part]
        elif isinstance(current, list):
            index = int(part)
            current = current[index]
        else:
            raise KeyError(part)
    return current


def ref_exists(ref: str, run_dir: Path | None) -> bool:
    if run_dir is None:
        return True
    artifact, _, pointer = ref.partition("#")
    if not artifact:
        return False
    path = run_dir / artifact
    if not path.exists():
        return False
    if not pointer:
        return True
    if path.suffix.lower() not in {".json"}:
        return True
    payload = load_json(path)
    try:
        pointer_get(payload, pointer)
    except Exception:
        return False
    return True


def validate(payload: dict, run_dir: Path | None = None) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    if payload.get("schema_version") != "1.0":
        errors.append("agent_orchestration: schema_version must be 1.0")

    required_agents = set(payload.get("required_agents", []))
    if required_agents != REQUIRED_AGENTS:
        missing = sorted(REQUIRED_AGENTS - required_agents)
        extra = sorted(required_agents - REQUIRED_AGENTS)
        if missing:
            errors.append("agent_orchestration: missing required_agents " + ", ".join(missing))
        if extra:
            errors.append("agent_orchestration: unexpected required_agents " + ", ".join(extra))

    invocations = payload.get("invocations")
    if not isinstance(invocations, list) or not invocations:
        errors.append("agent_orchestration: missing invocations")
        invocations = []

    by_agent: dict[str, dict] = {}
    for idx, invocation in enumerate(invocations, start=1):
        if not isinstance(invocation, dict):
            errors.append(f"invocations[{idx}]: must be an object")
            continue
        agent = str(invocation.get("agent", "")).strip()
        if agent in by_agent:
            errors.append(f"agent_orchestration: duplicate invocation for {agent}")
        if agent:
            by_agent[agent] = invocation
        if agent not in REQUIRED_AGENTS:
            errors.append(f"invocations[{idx}]: unexpected agent {agent!r}")
        if invocation.get("status") != "completed":
            errors.append(f"invocations[{idx}]: {agent or '<missing-agent>'} status must be completed")
        if invocation.get("blocking") is not True:
            errors.append(f"invocations[{idx}]: {agent or '<missing-agent>'} must be blocking=true")
        for field in [
            "stage",
            "input_refs",
            "output_refs",
            "decision",
            "decision_summary",
            "consumed_by",
        ]:
            if not has_text(invocation.get(field)):
                errors.append(f"invocations[{idx}]: {agent or '<missing-agent>'} missing {field}")
        for veto in invocation.get("vetoes", []):
            if isinstance(veto, dict) and veto.get("severity") == "blocking":
                errors.append(f"invocations[{idx}]: {agent} has unresolved blocking veto: {veto.get('reason', '')}")
        for field in ["input_refs", "output_refs", "consumed_by"]:
            refs = invocation.get(field, [])
            if not isinstance(refs, list):
                errors.append(f"invocations[{idx}]: {field} must be a list")
                continue
            for ref in refs:
                if not isinstance(ref, str) or not ref.strip():
                    errors.append(f"invocations[{idx}]: {field} contains an empty ref")
                elif not ref_exists(ref, run_dir):
                    errors.append(f"invocations[{idx}]: {field} ref does not exist: {ref}")

    missing_invocations = sorted(REQUIRED_AGENTS - set(by_agent))
    for agent in missing_invocations:
        errors.append(f"agent_orchestration: missing completed invocation for {agent}")

    expert = by_agent.get("google_omni_prompt_expert_agent")
    if expert:
        output_blob = " ".join(str(ref) for ref in expert.get("output_refs", []))
        if "08_google_omni_video_prompts.json#/segments" not in output_blob:
            errors.append("google_omni_prompt_expert_agent: output_refs must include 08_google_omni_video_prompts.json#/segments")

    gates = payload.get("stage_gates")
    if not isinstance(gates, list) or not gates:
        errors.append("agent_orchestration: missing stage_gates")
        gates = []
    for idx, gate in enumerate(gates, start=1):
        if not isinstance(gate, dict):
            errors.append(f"stage_gates[{idx}]: must be an object")
            continue
        gate_name = str(gate.get("gate", f"gate-{idx}"))
        if gate.get("next_allowed") is not True:
            errors.append(f"{gate_name}: next_allowed must be true before downstream artifacts are valid")
        blockers = gate.get("blockers", [])
        if isinstance(blockers, list) and blockers:
            errors.append(f"{gate_name}: blockers must be empty")
        for required in gate.get("requires_completed", []):
            invocation = by_agent.get(required)
            if not invocation or invocation.get("status") != "completed":
                errors.append(f"{gate_name}: required agent not completed: {required}")

    return errors, warnings


def main() -> int:
    if len(sys.argv) not in {2, 3}:
        print("usage: validate_agent_orchestration.py <05_agent_orchestration.json> [run_dir]", file=sys.stderr)
        return 2

    payload = load_json(Path(sys.argv[1]))
    run_dir = Path(sys.argv[2]).resolve() if len(sys.argv) == 3 else None
    errors, warnings = validate(payload, run_dir)
    result = {
        "ok": not errors,
        "error_count": len(errors),
        "warning_count": len(warnings),
        "errors": errors,
        "warnings": warnings,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
