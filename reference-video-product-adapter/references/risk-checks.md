# Risk Checks

## Source Trace Checker

Fail when:

- a product benefit has no source and is not marked `needs_confirmation`,
- a shot includes a claim not present in product materials,
- an on-screen text line states unsupported performance, certification, price, award, or guarantee,
- `source_refs` is empty for a product shot.

Allowed source types:

- product_pack
- reference_video
- user_instruction
- inference
- manual_confirmation

## AI Video Feasibility Checker

Flag risk when:

- more than 9 shots for a short single generation,
- more than 2 primary characters,
- more than 3 distinct locations,
- exact logo/package text is expected from the video model,
- product shape must remain exact but no product reference is supplied,
- too many fast cuts are requested for the target platform,
- storyboard text is overloaded.

Recommended fix:

- reduce shots,
- split into multiple generations,
- add product reference,
- move long text to post-production,
- make storyboard panels simpler.

## Similarity Risk Checker

Flag high risk when:

- exact reference copy is reused,
- original brand marks or character identity are reused,
- 3 or more consecutive beats keep the same subject, action, composition, and timing,
- the new shot list follows the reference frame-by-frame with only product swap,
- the final reveal mimics a distinctive protected sequence.

Recommended fix:

- keep pacing but alter subject/action/setting,
- change camera angle or shot order,
- replace distinctive transitions,
- add product-specific narrative logic,
- document the adaptation boundary.
