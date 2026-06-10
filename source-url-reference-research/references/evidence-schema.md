# Evidence Schema

Use this schema for Markdown tables, CSV rows, or JSON records.

## Required Fields

- `rank`
- `title`
- `source_url`
- `source_type`
- `brand_or_creator`
- `category`
- `static_or_moving`
- `duration_if_video`
- `why_selected`
- `visual_mechanism`
- `fit_for_project`
- `risks_or_limits`
- `confidence`

## Confidence Labels

- `verified`: opened or confirmed at the original/official source.
- `probable`: source is plausible but not original or not fully checked.
- `unconfirmed_lead`: discovery clue only; needs original source confirmation.
- `rejected`: kept only as a negative example or search-path note.

## Source Rules

- Use the original brand, creator, studio, agency, production company, or platform page when available.
- Keep reposts only as clues unless the original source cannot be found.
- Never treat downloaded media files as the evidence source. The evidence is the page URL and notes about what was observed there.
- Include access limitations instead of hiding them: login required, region blocked, removed, private, paywalled, low resolution, or duration unknown.
