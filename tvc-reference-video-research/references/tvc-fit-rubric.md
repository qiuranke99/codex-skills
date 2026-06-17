# TVC Fit Rubric

Use this reference to rank candidates after source verification. It is a judgment tool, not a substitute for watching the reference.

## Role Taxonomy

| Role | Definition | Use |
| --- | --- | --- |
| `direct_competitor` | Same category, similar use case, similar commercial task. | Highest strategic evidence, highest similarity risk. |
| `adjacent_category` | Neighboring category with transferable advertising grammar. | Fill gaps in model performance, ritual, lighting, or product-use structure. |
| `craft_analogy` | Different category, one useful mechanism. | Borrow texture, camera, light, edit, sound, or art direction only. |
| `rejected_noise` | Looks attractive but cannot support the brief. | Keep only as rejection evidence or source-recovery clue. |

## Hard Rejects

Reject from final ranked references when any applies:

- no reachable source page;
- non-video or only thumbnail/search snippet;
- tutorial, review, UGC, shopping page, stock footage, AI render, template, showreel, compilation, BTS, or case film not requested by the user;
- no brand, creator, platform, or accountable source evidence;
- conflicts with hard brief constraints such as indoor/model-led/premium/body-use;
- visually beautiful but offers no product role, no shot structure, and no transferable mechanism.

## 100-Point Scoring

Use the score for ranking; do not hide weaker source confidence behind high craft scores.

| Criterion | Points | What To Inspect |
| --- | ---: | --- |
| Category / brief fit | 12 | Same product, scene, audience, market tier, and commercial task. |
| Production value | 10 | Cinematography, grading, set, movement, post finish. |
| Casting / performance | 8 | Model presence, action believability, product handling, body language. |
| Shot language | 10 | Establishing, gesture, texture, product reveal, packshot, end frame. |
| Product role | 10 | Product drives the film, not just appears at the end. |
| Texture / macro proof | 8 | Skin, oil, liquid, material, absorption, highlight behavior. |
| Lighting | 8 | Transferable light logic: direction, contrast, skin response, reflections. |
| Art direction | 8 | Space, props, textiles, surfaces, color, brand tier. |
| Edit rhythm | 7 | TVC-compatible timing, cut logic, opening hook, payoff. |
| Sound / music | 5 | Sound design, material cues, music discipline, brand tonality. |
| Duration / format | 4 | Useful for 15/30/45s structure or cutdown logic. |
| Source credibility | 10 | Brand/creator/production/agency/archive reliability. |

Recommended adjustment:

```text
rank_score = base_score * source_confidence * lane_weight
```

- `source_confidence`: official or production source 1.0; industry media 0.85; browser-verified social/platform source 0.7; repost/compilation clue 0.3.
- `lane_weight`: direct competitor 1.05; adjacent category 1.0; craft analogy 0.85; rejected/noise 0.

## Body-Oil-Specific Signals

Positive:

- body/skin application gesture, not just face or product tabletop;
- oil pour, hand spread, skin sheen, absorption, droplet, reflection, or viscous movement;
- indoor bathroom/bedroom/spa/window-light world with controlled premium restraint;
- model performance that feels commercial and believable, not influencer tutorial;
- product bottle/packshot authority and legible product role;
- 20-45s structure or clearly extractable 15/30s cutdown logic.

Negative:

- fragrance fantasy with no body-care causality;
- hair-oil glamour mislabeled as body-oil strategy;
- liquid simulation with no person, product, or use context;
- oversexualized body imagery that harms skincare trust;
- over-smoothed skin that erases oil texture;
- hotel/luxury cliches that do not match budget or brand tier;
- product appears only in the final second.

## Common "Beautiful But Wrong" Failures

- Fashion film: strong mood, weak product causality.
- Perfume film: high craft, wrong functional promise.
- Stock liquid macro: good texture, no brand/product/use structure.
- Mass-market ad: direct category, wrong tier.
- Outdoor travel film: high production value, wrong scene.
- Showreel: impressive fragments, no original timing or end frame.
- Repost: plausible content, no verified source chain.

## Source Anchors

These sources are useful judging anchors, not authority shortcuts:

- Cannes Lions Film emphasizes the commercial film category and broader idea/execution/impact context: https://www.canneslions.com/awards/lions/film/what-you-need-to-know
- Cannes Lions Film Craft separates craft execution such as direction, cinematography, editing, sound, and production design: https://www.canneslions.com/awards/lions/film-craft/what-you-need-to-know
- AICP Awards category structure is a practical craft taxonomy for commercials and music videos: https://aicpawards.awardcore.com/about
- D&AD Entry Kit is a useful external index for advertising craft categories: https://media.dandad.org/documents/Entry_Kit_2026_ENG.pdf
- Effie entry guidance is a reminder that creative work should connect to strategic challenge, idea, and effectiveness logic: https://effie.org/partners/united-states/entry-details/review-entry-guidelines/
