#!/usr/bin/env python3
"""Build a local, dependency-free review gallery from validated run artifacts."""

from __future__ import annotations

import argparse
import html
import sys
from pathlib import Path
from typing import Any

from _contract_utils import ContractError, parse_timestamp, read_json, read_jsonl, write_text_atomic
from _url_policy import public_http_host


def _text(value: Any) -> str:
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    return "" if value is None else str(value)


def _safe_public_url(value: Any) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        public_http_host(value)
    except ContractError:
        return None
    return value


def _rationale_by_id(selection: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for item in selection.get("items", []):
        if isinstance(item, dict) and isinstance(item.get("candidate_id"), str):
            result[item["candidate_id"]] = {
                key: value
                for key, value in item.items()
                if key
                in {
                    "why_fit",
                    "decision_supported",
                    "transferable_mechanism",
                    "do_not_copy",
                    "dominance_dimension",
                    "dominance_reason",
                    "stronger_candidate_class",
                    "dominated_by_candidate_ids",
                    "reuse_condition",
                }
            }
    return result


def _card(
    candidate: dict[str, Any],
    rationale: dict[str, Any],
    receipt: dict[str, Any] | None,
    state: str,
) -> str:
    cid = html.escape(_text(candidate.get("candidate_id")))
    object_data = candidate.get("object", {})
    source_data = candidate.get("source", {})
    diversity_data = candidate.get("diversity", {})
    title = html.escape(_text(object_data.get("title") or cid))
    raw_url = object_data.get("canonical_url")
    safe_url = _safe_public_url(raw_url)
    if raw_url and safe_url is None:
        raise ContractError(f"candidate {candidate.get('candidate_id')} has an unsafe canonical URL")
    url = html.escape(_text(safe_url), quote=True)
    modality = html.escape(_text(candidate.get("modality")))
    family = html.escape(_text(source_data.get("source_family_id")))
    territory = html.escape(_text(diversity_data.get("territory_id")))
    verified_at = html.escape(_text((receipt or {}).get("checked_at")))
    access = (receipt or {}).get("access_state", {})
    access_label = html.escape(
        f"{_text(access.get('mode'))}/{_text(access.get('state'))}" if isinstance(access, dict) else ""
    )
    rationale_rows = "".join(
        f"<dt>{html.escape(str(key))}</dt><dd>{html.escape(_text(value))}</dd>"
        for key, value in rationale.items()
    )
    link = f'<a href="{url}" rel="noreferrer noopener">Open canonical item</a>' if url else "No URL"
    return f"""
      <article class="card {html.escape(state)}">
        <header><span class="badge">{html.escape(state)}</span><span>{modality}</span></header>
        <h2>{title}</h2>
        <p class="id">{cid}</p>
        <p>{link}</p>
        <dl>
          <dt>Source family</dt><dd>{family}</dd>
          <dt>Territory</dt><dd>{territory}</dd>
          <dt>Access</dt><dd>{access_label}</dd>
          <dt>Verified</dt><dd>{verified_at}</dd>
          {rationale_rows}
        </dl>
      </article>
    """


def build_gallery(run_dir: str | Path) -> str:
    root = Path(run_dir)
    candidates = read_jsonl(root / "02_candidates/candidate_ledger.jsonl")
    receipts = read_jsonl(root / "03_verification/verification_receipts.jsonl")
    selected = read_json(root / "04_selection/selected_20.json")
    rejected = read_json(root / "04_selection/rejected_10.json")
    candidate_by_id = {item.get("candidate_id"): item for item in candidates}
    receipts_by_id: dict[str, list[dict[str, Any]]] = {}
    for receipt in receipts:
        cid = receipt.get("candidate_id")
        if isinstance(cid, str):
            receipts_by_id.setdefault(cid, []).append(receipt)
    receipt_by_id: dict[str, dict[str, Any]] = {
        cid: max(items, key=lambda item: parse_timestamp(item.get("checked_at")))
        for cid, items in receipts_by_id.items()
    }
    selected_rationale = _rationale_by_id(selected)
    rejected_rationale = _rationale_by_id(rejected)
    selected_cards = []
    for cid in [item["candidate_id"] for item in selected.get("items", [])]:
        if cid not in candidate_by_id:
            raise ContractError(f"selected candidate {cid} is missing from ledger")
        selected_cards.append(_card(candidate_by_id[cid], selected_rationale.get(cid, {}), receipt_by_id.get(cid), "selected"))
    rejected_cards = []
    for cid in [item["candidate_id"] for item in rejected.get("items", [])]:
        if cid not in candidate_by_id:
            raise ContractError(f"rejected candidate {cid} is missing from ledger")
        rejected_cards.append(_card(candidate_by_id[cid], rejected_rationale.get(cid, {}), receipt_by_id.get(cid), "rejected"))
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Advertising Reference Review Board</title>
  <style>
    :root {{ color-scheme: light dark; font-family: ui-sans-serif, system-ui, sans-serif; }}
    body {{ margin: 0; padding: 2rem; background: #111318; color: #f5f5f5; }}
    h1 {{ margin: 0 0 .4rem; }} .lede {{ color: #adb5c5; max-width: 70rem; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit,minmax(290px,1fr)); gap: 1rem; }}
    .card {{ border: 1px solid #343946; border-radius: 14px; padding: 1rem; background: #1b1f27; }}
    .card.rejected {{ opacity: .78; }} header {{ display:flex; justify-content:space-between; color:#adb5c5; }}
    .badge {{ text-transform:uppercase; letter-spacing:.08em; font-size:.72rem; }}
    .selected .badge {{ color:#7ee2a8; }} .rejected .badge {{ color:#e9b872; }}
    h2 {{ font-size:1.05rem; }} .id {{ font-family:ui-monospace,monospace; color:#8d96a8; }}
    a {{ color:#8dc7ff; }} dl {{ display:grid; grid-template-columns:8.5rem 1fr; gap:.35rem .6rem; }}
    dt {{ color:#9ea7b7; }} dd {{ margin:0; overflow-wrap:anywhere; }} section {{ margin-top:2.5rem; }}
  </style>
</head>
<body>
  <h1>Advertising Reference Review Board</h1>
  <p class="lede">20 selected references and the 10 qualified references they dominated. Links were verified only at their recorded timestamps; access is not reuse permission.</p>
  <section><h1>Selected 20</h1><div class="grid">{''.join(selected_cards)}</div></section>
  <section><h1>Qualified but rejected 10</h1><div class="grid">{''.join(rejected_cards)}</div></section>
</body>
</html>
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    try:
        rendered = build_gallery(args.run_dir)
        output = Path(args.output)
        root = Path(args.run_dir)
        protected_inputs = (
            root / "02_candidates/candidate_ledger.jsonl",
            root / "03_verification/verification_receipts.jsonl",
            root / "04_selection/selected_20.json",
            root / "04_selection/rejected_10.json",
        )
        resolved_output = output.expanduser().resolve(strict=False)
        if any(resolved_output == item.expanduser().resolve(strict=False) for item in protected_inputs):
            raise ContractError("gallery output must not overwrite a source contract artifact")
        write_text_atomic(output, rendered)
    except ContractError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
