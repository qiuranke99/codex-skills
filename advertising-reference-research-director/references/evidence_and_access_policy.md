# Evidence And Access Policy

This file governs candidate granularity, evidence levels, browser/media verification, provenance, freshness, Chrome handling, and rights labels. The machine contract is `verification_receipt.schema.json`; this policy explains what its fields must prove.

## 1. Exact Candidate Unit

### Image

One candidate is one exact image inside an accountable item/project page. It requires:

- canonical item URL;
- stable image ID, asset locator, DOM locator, or schema-approved equivalent;
- enough observable content to prove it is the intended image;
- work/project context and accountable source.

A search thumbnail, generic gallery home, creator profile, project page with no target locator, or locally remembered image is not a candidate.

### Video

One candidate is one exact playable work or declared cut/version. It requires:

- canonical item URL;
- stable work/video/player ID or locator;
- title/work identity and version/region when material;
- real media playback evidence;
- accountable source or provenance chain.

A thumbnail, trailer card for a different work, channel/profile page, showreel index, embed shell, or title-only article is not a candidate.

## 2. Evidence Levels

Use these levels consistently:

- `E0_LEAD` — model memory, verbal mention, query idea, or unvisited URL. Never eligible.
- `E1_INDEXED` — search result/snippet or source index exposes a plausible item. Never eligible.
- `E2_PAGE_OPENED` — page opens but exact target media/object is not yet proven. Never eligible.
- `E3_MEDIA_CONFIRMED` — exact image renders or exact video playback advances, but provenance/object evidence is incomplete. Never eligible.
- `E4_QUALIFIED` — exact media, object match, accountable provenance, access mode, and fresh receipt all pass. Minimum level for the qualified 30.

The current machine contract intentionally stops at E4. Do not label an item E5: independent corroboration needs a future structured contract that binds the second source, second verifier, material claim, and conflict resolution. Extra corroboration may be retained as supporting evidence without upgrading the machine level.

Search snippets, HTTP status, metadata, or prestige cannot promote an item directly to E4.

## 2A. Run Modes And Capture Binding

Every intent freezes exactly one mode:

- `production_live`: require `approval.approved_at <= registration.frozen_at`
  and freeze the immutable plan strictly before the earliest recorded
  `approach.started_at`, `candidate.discovered_at`, or `capture.captured_at`;
  retain direct browser source records and use the
  `--require-production-contract-eligible` validator flag;
- `test_fixture`: synthetic contract data only;
- `retrospective_smoke`: historical imported evidence whose original plan was not preregistered.

Every E4 receipt binds one or more canonicalized records in `browser_capture_records.jsonl`. The bindings must jointly cover access, media, object match, and provenance; the latest capture time equals `checked_at`. Capture records include their origin, operator, browser surface, frozen plan hash, structured observations, and retained source-record hash/pointer.

These are integrity bindings, not digital signatures. `signed_chrome` means a
logged-in browser context, never a cryptographically signed observation.
Fixture and retrospective records can pass their own acceptance class but can
never satisfy the production-contract-eligible gate. Even a production-live
contract PASS remains `production_deliverable=false`; any delivery or browser
action claim requires a separate trusted external attestation that is not
self-declared inside the run.

## 3. Verification Independence

The verification receipt must name a verifier who did not discover that candidate. A separate authenticated-source operator may supply browser observations, but the verifier still evaluates the receipt and provenance. The finder cannot set final qualification status.

Automated checks may establish transport, redirect, media metadata, hashes, or timestamps. Human/browser inspection is required wherever the check depends on rendered content, exact-object match, login state, player behavior, or misleading page semantics.

## 4. Access Check

Record both access mode and observed access state. Use the schema enums exactly:

- `access_state.mode`: `public | signed_chrome | subscription | geo_or_age_gated`;
- `access_state.state`: `accessible | session_bound | blocked | challenge | soft_404 | not_found`.

A passing candidate must use `accessible` or an authorized `session_bound` state and be viewable in its recorded mode at verification time. Preserve HTTP/browser details in `checked_url`, `http_status`, `page_rendered`, `canonical_url_resolved`, `shareable_without_session`, and `challenge_detected`.

Check and record:

1. requested and final canonical URL;
2. redirect chain when material;
3. page render state;
4. hard 404/410 and server errors;
5. soft 404, deleted/private notice, empty shell, challenge/CAPTCHA, consent wall, geo/age gate, or subscription/login dependency;
6. whether the exact item has a stable locator;
7. whether a recipient can recheck it without the same session;
8. fallback URL when available.

HTTP 200 is transport evidence only. A challenge page, soft 404, private post, empty player, or irrelevant redirect fails qualification even when status is 200.

The local URL policy rejects credentials, non-HTTP(S) schemes, localhost-style hosts, and private/reserved IP literals. It deliberately does not resolve DNS or fetch remote content, so it is not a standalone SSRF or DNS-rebinding defense. Browser operators must inspect the final rendered origin; downstream systems that fetch URLs need their own DNS-resolution, redirect, and network-egress controls. The review gallery links to canonical pages and never embeds or fetches remote media.

Use the schema structures exactly:

- `media_check = {status, kind, image_render, video_playback}` where `status` is `passed | failed | not_applicable`, `kind` is `image | video`, and exactly the modality-relevant evidence object is populated. Every qualified candidate requires `status: passed`.
- `provenance_check = {status, accountable_url, accountable_owner, source_signal, matched_object}` where `status` is `passed | failed` and `source_signal` is `original_owner | creator_credit | accountable_curator | official_distribution | discovery_only`. Every qualified candidate requires `status: passed`, `matched_object: true`, and a signal other than `discovery_only`.

## 5. Image Media Check

For an image to pass:

- the exact target image renders, not only a placeholder or blurred unloaded proxy;
- natural dimensions or equivalent render evidence are nonzero and plausible;
- the shorter edge is at least 240 pixels and total area is at least 230,400 pixels;
- the candidate's asset locator resolves to the observed image inside the canonical item;
- the visual content matches the candidate description and frozen brief evidence;
- the image is not a duplicate or unintended crop masquerading as a different work;
- screenshot/proxy capture, if used, is limited to evidence/review needs and respects access/rights policy.

Do not promote a project page with several images unless the chosen image is individually locatable and described.

## 6. Video Media Check

For a video to pass:

- the exact intended work/cut is present;
- both a stable work ID and a concrete player/asset locator are present;
- the player is not merely a poster, disabled embed, error surface, or unrelated reel;
- playback begins or resumes and the media time advances by an observable positive interval;
- duration and version/region are recorded when observable and material;
- sampled content matches the title, candidate description, and decision evidence;
- a verifier samples enough of the work to evaluate the claimed mechanism; full viewing is preferred for short advertising work;
- autoplay animation, page background, or GIF is not mistaken for the target video.

Record playback evidence such as initial time, later time, observed advancement, sampled ranges, and player state. A network media request without content/object confirmation is insufficient.

## 7. Object-Match Check

The verifier compares rendered media against the candidate claim and frozen intent. Record concrete observations:

- subject and campaign/work identity;
- scene scale and human presence;
- relevant visual or temporal mechanism;
- version/cut/region when applicable;
- any contradiction or uncertainty.

Generic praise such as “premium”, “cinematic”, “beautiful”, or “on brief” is not evidence.

## 8. Provenance Check

An accountable source identifies at least one responsible entity and the work being shown. Preferred order:

1. original brand, creator, director, photographer, studio, production company, agency, or official campaign page;
2. professional archive, award, trade publication, or curated source with work identity and credits;
3. social post by an accountable original participant;
4. repost/aggregator only as discovery, followed by origin recovery.

Record source family, source role, signal type, accountable entity, evidence URL, and any corroborating URL. Style resemblance does not prove authorship. If origin cannot be recovered, the candidate cannot reach E4 unless the specialist source itself is accountable for the item and the uncertainty is not material.

## 9. Receipt Requirements

Every qualification receipt must bind:

- `receipt_id`, `run_id`, `candidate_id`, `intent_id`, `intent_version`, `pack_id`, `source_id`, and modality;
- `verifier.finder_agent_id`, `verifier.verifier_agent_id`, verification surface, and `independence_asserted: true`;
- `checked_at` in an unambiguous timezone plus a structured freshness window and expiry;
- canonical/final URL and access mode/state;
- page-render result;
- image-render plus asset-locator evidence, or video-player plus playback-advancement evidence;
- `object_match` observations and status;
- provenance result and source signal;
- evidence level;
- capture-record ID/hash bindings whose declared purposes jointly cover access, media, object match, and provenance;
- public shareability/fallback state;
- six-dimensional rights/access labels;
- `dedup_check`, the validator-recomputed final comparison-set hash, fixed
  perceptual threshold, and fingerprint-capture IDs;
- outcome and explicit failure codes;
- tool/browser evidence references without secrets.

A receipt cannot be copied from another URL or reused after a material page, version, route, or intent change. The final recheck may append or supersede a receipt but must preserve history.

`content_similarity_checked=true` is not evidence and is not part of the
contract. Each final image uses an exact-image SHA-256 plus 64-bit perceptual
hash; each final video uses a sampled-frame manifest SHA-256 plus 64-bit
perceptual signature with at least three strictly increasing declared timestamps
that all fall within the receipt-bound video duration. The fingerprint
must appear in the hash-bound media capture and match the candidate. Every final
receipt binds the exact final-30 fingerprint projection. `authorized_version`
requires a shared near-duplicate group and a referenced, schema-valid manual
version review; exact URL, stable-ID, or exact-fingerprint collisions always
fail.

## 10. Chrome And Authenticated Sources

Use an already-authorized signed-in Chrome session only when the user's access policy permits it and the source materially improves the research. Invoke the available Chrome-control workflow and assign one authenticated-source operator to prevent tab/session contention.

Rules:

- inspect only pages needed for the brief;
- never reveal account names, profile identity, cookies, tokens, headers, private messages, recommendations unrelated to the task, or subscription data;
- never change account settings, follow/like/comment/message, purchase, or post unless separately requested and authorized;
- label session evidence `browser_verified_login_context`;
- set `shareable_without_session=true` only when a session-free public recheck succeeds, `false` when session dependence is observed, and `unknown` when session-free access was not tested;
- prefer a public canonical or fallback source when it proves the same object;
- do not persist screenshots that contain unrelated private UI;
- close/release controlled tabs according to the Chrome-control contract.

Logged-in visibility proves only that the authorized session could view the item at the recorded time.

## 11. Rights Matrix

Keep these six states separate for every candidate:

| Dimension | Meaning |
|---|---|
| `discoverable` | The source may be searched or encountered. |
| `viewable` | The recorded access context can render/play it. |
| `shareable_without_session` | Another recipient can open the canonical/fallback link without the verifying session. |
| `downloadable` | Evidence or explicit license permits downloading; technical possibility alone is not permission. |
| `internal_board_use` | Evidence or policy supports use in the declared internal review artifact. |
| `commercial_reuse` | Evidence supports reproduction/adaptation in commercial output. Usually `unknown`, `prohibited`, or `permission_required` without explicit license. |

Each dimension is an object with `state: allowed | prohibited | permission_required | unknown | not_applicable` and a non-empty `basis`. Do not infer a stronger right from a weaker one. Embedding a remote thumbnail in a review board must follow source terms and project policy; otherwise use a text link or authorized local review proxy.

For qualified reference research, `downloadable`, `internal_board_use`, and `commercial_reuse` fail closed: a self-declared basis cannot set them to `allowed`. A separate, retained authorization/clearance workflow is required before any stronger claim. `shareable_without_session` must agree exactly with the observed access state; logged-in visibility cannot self-assert a public link.

Image download is an optional, explicit branch after rights/access review. Video download is forbidden by this Skill unless the user separately authorizes it and the evidence supports it.

## 12. Freshness And Delivery Recheck

Define `delivery_reference_time` and `freshness_window_minutes` in the verification report. Default freshness is 30 minutes.

Before delivery:

1. recheck all 30 qualified candidates, not only the selected 20;
2. rerun exact media and access checks appropriate to modality;
3. confirm the canonical item still matches;
4. supersede stale receipts without erasing them; `verify_candidates.py` imports
   the existing output ledger before replacement, preserves every uniquely
   identified historical receipt in timestamp order, rejects foreign/stale
   run-intent-pack bindings and ambiguous same-time history, and evaluates
   `--require-qualified` against only the unambiguous latest receipt per candidate;
5. replace any failed candidate through the normal discovery, dedup, independent verification, and selection process;
6. rerun set, diversity, and audit gates after replacement.

Never promise future availability. State that evidence is valid at the recorded delivery time.

## 13. Quarantine Versus Rejection

Quarantine before the qualified 30 when any of these applies:

- hard/soft 404, private/deleted page, challenge, or inaccessible required session;
- no exact image locator or no advancing video playback;
- wrong object, wrong cut, or misleading title;
- unknown/unaccountable provenance below E4;
- exact or disallowed near-duplicate;
- unresolved rights/shareability conflict with a hard brief constraint;
- stale verification outside the delivery window.

Quarantined items receive failure evidence but never appear in `rejected_10.json`. The rejected 10 must all remain E4 at delivery.
