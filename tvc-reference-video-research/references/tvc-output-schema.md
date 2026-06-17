# TVC Output Schema

Use this schema for Markdown, JSON, or CSV evidence records.

## User-Facing Table

Keep the visible table compact:

| Column | Meaning |
| --- | --- |
| `Rank` | Final rank, not search order. |
| `Status` | verified, browser_verified, probable, etc. |
| `Reference` | Title and brand/creator. |
| `Source URL` | Evidence page, not CDN or downloaded file. |
| `Duration` | Duration and basis if known. |
| `Fit` | direct_category, adjacent_category, craft_analogy. |
| `Reference Role` | product_reveal, texture_proof, model_application, lighting, edit_rhythm, etc. |
| `What To Borrow` | Transferable mechanism. |
| `Do Not Copy` | Protected or too-specific expression. |
| `Risk` | Source, access, similarity, tier, or relevance limit. |

## Complete JSON Fields

```json
{
  "schema_version": "tvc_reference_video_evidence.v1",
  "research_id": "YYYY-MM-DD-brief-slug",
  "brief_digest": "",
  "audit": {
    "route_decision": "video_reference",
    "duration_target_sec": 30,
    "duration_acceptance_window_sec": [20, 45],
    "query_lanes": [],
    "queries_tried": [],
    "platforms_checked": [],
    "hard_exclusions": [],
    "verification_methods_used": [],
    "counts": {
      "pages_opened": 0,
      "candidates_collected": 0,
      "verified": 0,
      "probable": 0,
      "unconfirmed_leads": 0,
      "rejected": 0
    },
    "missing_source_tiers": [],
    "next_searches": []
  },
  "references": [
    {
      "rank": 1,
      "candidate_status": "verified",
      "title": "",
      "brand_or_client": "",
      "product_category": "",
      "source_url": "",
      "final_url": "",
      "source_tier": "tier_1_original",
      "source_type": "production_company",
      "platform": "",
      "video_kind": "single_work",
      "duration_sec": null,
      "duration_basis": "observed",
      "verification_method": "browser",
      "checked_at": "YYYY-MM-DDTHH:MM:SS+08:00",
      "brief_fit": "direct_category",
      "reference_role": "model_application; texture_proof",
      "visual_mechanism": "",
      "temporal_mechanism": "",
      "shoot_takeaway": "",
      "do_not_copy": "",
      "risks_or_limits": "",
      "rejection_reason": "",
      "confidence": "verified"
    }
  ],
  "unconfirmed_leads": [],
  "rejected_candidates": []
}
```

## Candidate Status Labels

- `verified`: source page opened and video relevance checked.
- `browser_verified`: verified in a browser.
- `browser_verified_partial`: visible but some metadata remains limited.
- `browser_verified_login_context`: visible only with current login context.
- `probable`: useful and plausible, but a critical fact is incomplete. Typical cases: source page opened but the video was not fully watched; duration or official ownership is incomplete; a JS-heavy page exposes enough title/creator evidence but needs browser verification. Keep below verified rows and mark the missing proof.
- `unconfirmed_lead`: discovery clue only; never final ranked evidence.
- `rejected`: inspected and excluded.
- `inaccessible`: blocked, removed, private, or not confirmable.
- `out_of_scope`: wrong source type or wrong creative task.

## Final Answer Template

```markdown
**Conclusion**
Prioritize `#1`, `#2`, and `#4`. Assign each reference a job: rhythm, product reveal, texture proof, lighting, or packshot authority. Do not blend all references evenly.

## Ranked TVC References

| Rank | Status | Reference | Source URL | Duration | Fit | Reference Role | What To Borrow | Do Not Copy | Risk |
| ---: | --- | --- | --- | ---: | --- | --- | --- | --- | --- |
| 1 | verified | ... | https://... | 30s | direct_category | texture_proof | ... | ... | ... |

## Shooting Decisions

| Decision | Recommendation |
| --- | --- |
| Core film feel | ... |
| Opening 0-5s | ... |
| Product first reveal | ... |
| Camera language | ... |
| Light and material | ... |
| Edit rhythm | ... |
| Art direction | ... |
| Packshot | ... |
| Sound/music | ... |
| Similarity risk | ... |

## Reference Roles

- `#1`: rhythm skeleton
- `#2`: product reveal
- `#3`: texture/lighting proof
- `#4`: transition or movement mechanism
- `#5`: packshot authority

## Unconfirmed Leads

| Lead | Why Useful | Missing Proof | Next Search |
| --- | --- | --- | --- |

## Rejected Candidates

| Candidate | Rejection Reason |
| --- | --- |

## Search Audit

- Route: `video_reference`
- Query lanes:
- Queries tried:
- Platforms checked:
- Hard exclusions:
- Verification:
- Missing tiers:
- Next searches:
```

## Validation

Run the validator on saved Markdown or JSON:

```bash
python scripts/validate_tvc_reference_report.py <report.md-or-json>
```

The validator catches the most damaging failures: missing search audit, missing source URL, unconfirmed leads in the final ranked table, and showreels/compilations presented as final references.
