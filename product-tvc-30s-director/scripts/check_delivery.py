#!/usr/bin/env python3
"""Check prompt lengths and a continuous timeline using the standard library.

UTF-8 files are decoded strictly without trimming, BOM removal, Unicode
normalization, or newline conversion. Each --prompt is one independent payload.
Total timeline duration defaults to 30 seconds and accepts any positive Decimal
via --duration or timeline JSON "total_seconds".
Exit codes: 0 = mechanical checks pass; 1 = check fails; 2 = invalid input.
No content, directing quality, visual stability, or provider acceptance is judged.
"""

from __future__ import annotations

import argparse
import json
import sys
from decimal import Decimal, DecimalException, localcontext
from pathlib import Path
from typing import Any


DEFAULT_TOTAL_SECONDS = Decimal("30")
MINIMUM_HOLD_SECONDS = Decimal("1")
MAX_SAFE_PRECISION = 4096


class InputError(ValueError):
    """An invalid CLI argument, file, or JSON document."""


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise InputError(message)


def positive_integer(value: str) -> int:
    try:
        result = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a positive integer") from exc
    if result <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return result


def nonnegative_integer(value: str) -> int:
    try:
        result = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a nonnegative integer") from exc
    if result < 0:
        raise argparse.ArgumentTypeError("must be a nonnegative integer")
    return result


def positive_decimal(value: str) -> Decimal:
    stripped = value.strip()
    if not stripped or stripped != value:
        raise argparse.ArgumentTypeError("must be a finite positive decimal number")
    try:
        result = Decimal(stripped)
    except DecimalException as exc:
        raise argparse.ArgumentTypeError("must be a finite positive decimal number") from exc
    if not result.is_finite() or result <= Decimal("0"):
        raise argparse.ArgumentTypeError("must be a finite positive decimal number")
    return result


def exact_sub(left: Decimal, right: Decimal) -> Decimal:
    """Subtract finite Decimals without context rounding within safe precision."""
    left_exp = int(left.as_tuple().exponent)
    right_exp = int(right.as_tuple().exponent)
    high = max(left.adjusted(), right.adjusted(), 0) + 2
    low = min(left_exp, right_exp, 0)
    needed_prec = max(28, high - low + 5)
    if needed_prec > MAX_SAFE_PRECISION:
        raise InputError(f"decimal precision ({needed_prec}) exceeds safe limit ({MAX_SAFE_PRECISION})")
    with localcontext() as ctx:
        ctx.prec = needed_prec
        return left - right


def format_duration(value: Decimal) -> int | str:
    if value == value.to_integral_value() and abs(int(value.adjusted())) <= MAX_SAFE_PRECISION:
        return int(value)
    return str(value)


def read_utf8(path: Path) -> tuple[bytes, str]:
    try:
        raw = path.read_bytes()
        return raw, raw.decode("utf-8", errors="strict")
    except (OSError, UnicodeError, ValueError) as exc:
        raise InputError(f"cannot read UTF-8 file {str(path)!r}: {exc}") from exc


def check_prompt(
    path: Path, limit: int | None = None, reserve: int = 0,
    count_unit: str = "codepoints",
) -> dict[str, Any]:
    raw, body = read_utf8(path)
    codepoints = len(body)
    utf16_units = len(body.encode("utf-16-le")) // 2
    counted_units = codepoints if count_unit == "codepoints" else utf16_units
    effective_limit = None if limit is None else limit - reserve
    within_limit = None if effective_limit is None else counted_units <= effective_limit
    return {
        "path": str(path),
        "codepoints": codepoints,
        "utf16_units": utf16_units,
        "utf8_bytes": len(raw),
        "count_unit": count_unit,
        "counted_units": counted_units,
        "limit": limit,
        "reserve": reserve,
        "effective_limit": effective_limit,
        "within_limit": within_limit,
        "passed": within_limit is not False,
    }


def reject_constant(value: str) -> None:
    raise InputError(f"non-finite JSON number is not allowed: {value}")


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise InputError(f"duplicate JSON object key: {key!r}")
        result[key] = value
    return result


def read_timeline(path: Path) -> Any:
    _, source = read_utf8(path)
    try:
        return json.loads(
            source, parse_int=Decimal, parse_float=Decimal,
            parse_constant=reject_constant, object_pairs_hook=unique_object,
        )
    except (json.JSONDecodeError, DecimalException, RecursionError) as exc:
        raise InputError(f"invalid timeline JSON in {str(path)!r}: {exc}") from exc


def finite_number(value: Any) -> bool:
    # JSON numbers are Decimal; bool is deliberately not treated as an integer.
    return isinstance(value, Decimal) and value.is_finite()


def resolve_total_seconds(
    payload: dict[str, Any], cli_duration: Decimal | None, errors: list[str],
) -> Decimal | None:
    if cli_duration is not None and (not finite_number(cli_duration) or cli_duration <= Decimal("0")):
        raise InputError("duration must be a finite positive Decimal")

    has_json_total = "total_seconds" in payload
    json_total = payload.get("total_seconds")
    json_valid = False
    if has_json_total:
        if not finite_number(json_total):
            errors.append("total_seconds must be a finite JSON number, not a boolean or string")
        elif json_total <= Decimal("0"):
            errors.append("total_seconds must be greater than 0 seconds")
        else:
            json_valid = True

    if cli_duration is not None:
        if json_valid and json_total != cli_duration:
            errors.append(
                f"total_seconds ({json_total}) does not match --duration ({cli_duration})"
            )
        return cli_duration
    if has_json_total:
        return json_total if json_valid else None
    return DEFAULT_TOTAL_SECONDS


def check_timeline(payload: Any, duration: Decimal | None = None) -> dict[str, Any]:
    errors: list[str] = []
    result: dict[str, Any] = {"passed": False, "errors": errors}
    if not isinstance(payload, dict):
        errors.append("timeline must be a JSON object")
        return result

    target_total = resolve_total_seconds(payload, duration, errors)
    shots = payload.get("shots")
    if not isinstance(shots, list) or not shots:
        errors.append("shots must be a nonempty array")
        return result

    seen: set[str] = set()
    previous_end: Decimal | None = None
    final_start: Decimal | None = None
    final_end: Decimal | None = None
    zero = Decimal("0")
    for index, shot in enumerate(shots):
        label = f"shots[{index}]"
        if not isinstance(shot, dict):
            errors.append(f"{label} must be an object")
            previous_end = None
            continue
        shot_id = shot.get("id")
        if not isinstance(shot_id, str) or not shot_id.strip():
            errors.append(f"{label}.id must be a nonempty string")
        elif shot_id in seen:
            errors.append(f"duplicate shot id: {shot_id!r}")
        else:
            seen.add(shot_id)

        start, end = shot.get("start"), shot.get("end")
        start_valid, end_valid = finite_number(start), finite_number(end)
        for name, value, valid in (("start", start, start_valid), ("end", end, end_valid)):
            if not valid:
                errors.append(f"{label}.{name} must be a finite JSON number, not a boolean or string")
            elif value < zero or (target_total is not None and value > target_total):
                bound = f"0 to {target_total}" if target_total is not None else "nonnegative"
                errors.append(f"{label}.{name} must be within {bound} seconds")

        if start_valid:
            if index == 0 and start != zero:
                errors.append("first shot must start at 0 seconds")
            elif index > 0 and previous_end is not None and start != previous_end:
                kind = "gap" if start > previous_end else "overlap"
                errors.append(f"{label} has a {kind}: start must equal the previous end")
        if start_valid and end_valid and end <= start:
            errors.append(f"{label} must have positive duration (end > start)")
        previous_end = end if end_valid else None
        if index == len(shots) - 1:
            final_start = start if start_valid else None
            final_end = end if end_valid else None

    if target_total is not None and final_end is not None and final_end != target_total:
        errors.append(f"last shot must end at exactly {target_total} seconds")

    hold_start = payload.get("hold_start")
    if not finite_number(hold_start):
        errors.append("hold_start must be a finite JSON number, not a boolean or string")
    else:
        if final_start is not None and final_end is not None:
            if not final_start <= hold_start < final_end:
                errors.append("hold_start must be inside the last shot: start <= hold_start < end")
        if target_total is not None:
            if exact_sub(target_total, hold_start) < MINIMUM_HOLD_SECONDS:
                max_hold_start = exact_sub(target_total, MINIMUM_HOLD_SECONDS)
                errors.append(
                    f"final declared hold must be at least 1 second: hold_start <= {max_hold_start}"
                )
            if hold_start < zero or hold_start > target_total:
                errors.append(f"hold_start must be within 0 to {target_total} seconds")
        elif hold_start < zero:
            errors.append("hold_start must be nonnegative")

    result.update({
        "passed": not errors,
        "shot_count": len(shots),
        "required_total_seconds": format_duration(target_total) if target_total is not None else None,
        "minimum_declared_hold_seconds": 1,
        "hold_start": str(hold_start) if finite_number(hold_start) else None,
        "note": "Checks declared timing only; actual visual stability is not assessed.",
    })
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = JsonArgumentParser(description=__doc__)
    parser.add_argument("--prompt", action="append", type=Path, default=[],
                        help="UTF-8 original payload file; repeat for independent submissions")
    parser.add_argument("--limit", type=positive_integer,
                        help="positive unit limit; omitted means count only")
    parser.add_argument("--reserve", type=nonnegative_integer, default=0,
                        help="units reserved from limit (default 0)")
    parser.add_argument("--count-unit", choices=("codepoints", "utf16"), default="codepoints")
    parser.add_argument("--timeline", type=Path,
                        help='JSON file: {"shots":[{"id":"S01","start":0,"end":30}],"hold_start":29}')
    parser.add_argument("--duration", type=positive_decimal,
                        help="positive total timeline duration in seconds (default: 30 or timeline total_seconds)")
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        args = build_parser().parse_args(argv)
        if not args.prompt and args.timeline is None:
            raise InputError("provide at least one --prompt or --timeline")
        if args.limit is None and args.reserve != 0:
            raise InputError("a nonzero --reserve requires --limit")
        if args.limit is not None and args.reserve > args.limit:
            raise InputError("--reserve must not exceed --limit")
        if args.duration is not None and args.timeline is None:
            raise InputError("--duration requires --timeline")
        prompts = [check_prompt(path, args.limit, args.reserve, args.count_unit) for path in args.prompt]
        timeline = None
        if args.timeline is not None:
            timeline = check_timeline(read_timeline(args.timeline), duration=args.duration)
            timeline["path"] = str(args.timeline)
        passed = all(item["passed"] for item in prompts) and (timeline is None or timeline["passed"])
        report = {"schema_version": 1, "scope": "mechanical_only", "passed": passed,
                  "prompts": prompts, "timeline": timeline}
        exit_code = 0 if passed else 1
    except InputError as exc:
        report = {"schema_version": 1, "scope": "mechanical_only", "passed": False,
                  "error": {"kind": "invalid_input", "message": str(exc)}}
        exit_code = 2
    # ASCII-safe JSON remains readable by machines even on legacy Windows consoles.
    print(json.dumps(report, ensure_ascii=True, allow_nan=False, indent=2))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
