# AI Video Shot Script Director Test Cases

Run:

```bash
python3 scripts/validate_shot_contract.py references/shot_contract.template.json
python3 scripts/test_contract.py
python3 scripts/test_asset_canon_bridge.py
python3 scripts/test_global_canon_write_gate.py
```

## Positive cases

1. **Structured poetic ad**: a 15-shot sensorial product script already contains timing, image intent and camera notes but no literal usage procedure. The Skill classifies `poetic_brand_film`, preserves associative montage, converts felt states into visible performance, closes 30 seconds and does not demand a usage demonstration.
2. **Functional ad with evidence**: an operating step and benefit are explicitly supplied with source IDs. The contract may use only those claim IDs, makes initial/action/end states literal and records unresolved exact copy without blocking unrelated shots.
3. **Sparse input**: a rough idea plus duration is enough. Ordinary lens, staging, movement, performance and cut decisions are inferred and logged.
4. **Selective shot repair**: a request to revise S004 changes S004 plus a proven adjacent continuity edge. Other shot UIDs and content remain stable; invalidation is limited and explained.
5. **Associative continuity**: rose petals cut to amber oil through texture and motion rhyme. The contract records conceptual continuity rather than inventing one physical location.
6. **Supplied copy preservation**: exact voice-over and on-screen copy keep their source IDs and timing intent; provisional non-claim copy remains visibly provisional.
7. **Legacy Word shot table**: a readable OLE `.doc` is converted with `textutil`; original bytes are hashed and shot number, timing, table order, and supplied copy survive extraction without asking the user to rewrite it.
8. **Predecessor-bound selective repair**: S004 revision binds one frozen predecessor, increases SemVer, declares the exact real JSON-pointer diff, and the validator independently derives S004 while all other stable Shot UIDs remain unchanged. Pass.
9. **Historical stale consumer**: stale, downstream-ineligible B1 retains its exact A1 dependency after A1 is superseded by A2, with a historical edge and one complete A2-to-B1 stale event. Pass.
10. **Atomic Canon delta**: the updater validates a raw-hash-locked immutable base snapshot against the actual post manifest and receipt; unchanged and explicitly preserved entries are byte-identical. Pass.
11. **Seven fixed asset owners**: every maintained character/product/packaging/material/scene owner exports its own approved binary asset and required prompt evidence through a package-local wrapper into one four-lock `ai-video-artifact-v1` Canon entry. Pass.
12. **Replacement closure**: replacing an asset supersedes the old entry, preserves its historical locks/edges, applies an event-bound stale overlay to direct and transitive consumers, and leaves their immutable owner records approved. Pass.
13. **Capability-bound packaging**: an ordinary packaging asset authorizes only `product_geometry`; only owner-approved `geometry_layout_exact_copy_verified` evidence authorizes `label_copy`. Pass.
14. **Crash-safe commit recovery**: a fault after atomic Canon replacement but before receipt publication leaves no `applied` receipt; an identical rerun reconstructs it from the immutable base/delta/record and exact post manifest. Pass.
15. **Concurrent exports**: two processes export different fixed-owner assets simultaneously; a project lock plus raw-byte compare-and-swap serializes them, and the final Canon contains both revisions with no lost update. Pass.
16. **Prepared-transaction resume**: faults after base/delta or after owner-record publication leave Canon untouched and no receipt; an exact rerun reuses identical immutable bytes and completes. Pass.
17. **Character terminal route**: casting without `--casting-as-terminal` is rejected; explicit terminal casting passes; no casting export plus final passes; terminal casting/final/single-face collide on one same-key terminal slot. Pass.
18. **Global cross-writer recovery**: Shot revisions plus Look, Storyboard, Previs, Keyframe, and Prompt writers all share one lock/journal; a successor recovers a committed missing receipt before advancing. Pass.
19. **Pinned raster runtime**: Shot Director and Prompt Director carry one identical exact Pillow pin, and real asset bytes must decode under it. Pass.

## Negative cases

1. **Time mismatch**: shot durations do not equal total duration within 0.01 seconds. Fail.
2. **Invented efficacy**: `used_claim_ids` names a benefit without a corresponding source-backed `supplied_claims` record. Fail.
3. **Hidden mode conversion**: a poetic film is rewritten as literal instruction merely because product usage details are absent. Fail.
4. **User homework**: the Skill asks the user for camera height, lens, blocking or visible performance instead of inferring them. Fail.
5. **Vague-only shot**: action is only “高级、电影感、被治愈” with no observable action path or ending state. Fail.
6. **Multiple unrelated moves**: one shot contains several competing camera trajectories instead of one primary movement. Fail.
7. **Unbounded selective edit**: an unrequested shot changes without a dependency reason. Fail.
8. **Display number as identity**: a reorder silently renames shot identity. Fail.
9. **False approval**: machine validation is described as user approval. Fail.
10. **Hash omission**: a frozen artifact omits the canonical hash or ignores a changed nested dependency hash. Fail.
11. **Claim hidden in copy**: dialogue or on-screen text uses a claim ID that is not source-backed and registered in `claim_boundary`. Fail.
12. **Malformed structure**: unhashable or wrong-typed list values return deterministic validation errors without a traceback. Fail closed.
13. **Self-reported revision**: a non-initial revision omits the actual predecessor, keeps the same SemVer, understates `changed_json_pointers` or changed Shot UIDs, or lists one artifact as both invalidated and preserved. Fail.
14. **Fake atomic delta**: receipt-only application uses a stale base, changes another owner's content, or mutates a declared preserved artifact. Fail.
15. **Fake history**: a current eligible consumer uses a superseded producer, the historical edge/event is missing, a superseded dependency lock is forged, or active-plus-superseded dependencies form a cycle. Fail.
16. **Asset-owner spoof**: a wrapper receives an owner override, an approval record names another owner, or a rehashed sidecar changes its fixed profile owner. Fail.
17. **Asset evidence escape/drift**: primary, prompt, approval or record locators escape project root, use absolute paths, or their bytes do not match the declared hashes. Fail.
18. **Unapproved asset**: assistant QA is not passed or no explicit user/external-pipeline production approval binds the exact asset, prompts, capability mode and Shot scope. Fail.
19. **Capability escalation**: geometry-only packaging self-adds `label_copy`, or any owner adds a control role outside its fixed authority mode. Fail.
20. **Broken replacement overlay**: a historical consumer remains eligible, the closure is incomplete, or the unique matching stale event is missing. Fail.
21. **False-applied receipt**: a receipt is written before Canon replacement/readback, or recovery binds a different/later post manifest. Fail.
22. **Lost update**: two exporters read one base and the later replace silently discards the earlier artifact instead of locking/re-reading or rejecting by compare-and-swap. Fail.
23. **Arbitrary binary visual asset**: text/blob bytes, a mismatched extension, an unreadable PNG/JPEG/WebP, or dimensions below 64×64 are presented as a character/product/scene control image. Fail.
24. **Forged image header**: a CRC-correct PNG advertises 1024×1024 in IHDR but its IDAT cannot decode that raster. Full decoder verification/load fails. Fail.
25. **Character route spoof**: casting omits its explicit terminal flag, approval changes `authority_stage`/`terminal_route_decision`, or a different character owner tries to replace the same terminal slot. Fail.
26. **Global gate bypass**: any existing-Canon writer writes directly, crosses another prepared transaction, resumes with different registered/preserved IDs, or publishes receipt before durable post readback. Fail.

## Completion evidence

The template and JSON Schema must parse, contract/manifest/source-ingestion tests must exit zero, positive fixtures must pass, adversarial fixtures must fail for the expected reason, and the package must contain no model-specific provider binding or post-production responsibility.
