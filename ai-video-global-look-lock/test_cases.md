# AI Video Global Look Lock Test Cases

Run:

```bash
python3 scripts/validate_global_look.py references/global_look_contract.template.json
python3 scripts/test_contract.py
```

## Positive cases

1. **Single scene / one State**: one coherent environment and lighting family has one hero reference, one Look State, complete product/skin boundaries and exact downstream inheritance. Pass.
2. **Multiple scenes / multiple States**: exterior, tactile macro and practical-lit interior share one Core but have explicit State rules and visual coverage. Every shot maps exactly once. Pass.
3. **No user look image**: derive a provisional Core from the approved Shot Contract, independently generate only missing references, inspect them later, and freeze after boundary checks. Pass.
4. **Supplied treatment image**: use it for declared palette/contrast/lighting evidence only; retain product, character and scene truth from their approved assets. Pass.
5. **Shot Delta repair**: reduce diffusion around a label for one shot while retaining Core, State, product color and material. Invalidate only that Shot UID's look-applied outputs. Pass.
6. **Risk proof**: product/material and character/skin risks each map to known States, approved independent references and affected Shot UIDs. Pass.
7. **Prompt inheritance**: every downstream unit and repair prompt injects exact Core, assigned exact State, then legal Shot Delta; the same global look is therefore active in keyframes and video prompts. Pass.
8. **First-class visual references**: every internal State reference maps to a distinct nested artifact, real image bytes, complete owned-record sidecar, active Canon entry, and the root-plus-references receipt. Pass.
9. **Predecessor-bound State/Delta repair**: the revision binds one frozen predecessor, increases SemVer, records the exact real JSON-pointer diff, and the validator derives changed Core/State/reference/Shot scope rather than trusting the declaration. Pass.

## Negative cases

1. **Color card only**: a palette swatch is claimed as a complete global look with no lighting, contrast, material, skin or State evidence. Fail.
2. **Missing State proof**: a multi-State project has no approved visual reference for one State. Fail.
3. **Product recolor**: a warm grade changes verified package white or amber liquid base color. Fail.
4. **Material rewrite**: frosted glass becomes glossy, transparent oil becomes opaque, or metallic finish becomes iridescent. Fail.
5. **Skin identity drift**: the look whitens, tans, smooths, de-ages or reshapes the approved character. Fail.
6. **One literal exposure everywhere**: materially different scenes are forced into one exposure/color temperature instead of legal States. Fail.
7. **Reference-board crop**: model references are cropped from one generative multi-panel board. Fail.
8. **Uninspected reference**: a generated image is marked approved in the generation turn without later inspection. Fail.
9. **Partial Core invalidation**: Look Core changes but only one shot's storyboard/keyframe/prompt is invalidated. Fail.
10. **Paraphrased inheritance**: downstream prompts say “same look as before” instead of injecting the complete global block and binding its version. Fail.
11. **Broken hash**: changing a nested dependency hash does not change the artifact hash. Fail.
12. **Declared but unproved risk**: a product/material or skin risk remains `planned` when the artifact claims approval. Fail.
13. **Private manifest fork**: the Look package copies its own `PROJECT_CANON_MANIFEST.json` instead of an atomic delta receipt against the one project registry. Fail.
14. **Reference alias impersonation**: an internal `reference_id` is sent downstream as if it were an artifact ID, or a forged artifact ID is substituted. Fail.
15. **Unregistered/tampered visual reference**: the nested artifact is absent from Canon/receipt, its scope differs from assigned States, primary bytes drift, or its record-sidecar hash is pseudo/tampered. Fail.
16. **Self-reported selective scope**: predecessor bytes are absent or forged, SemVer is unchanged, a second State/Shot/reference field is hidden from the diff, or one artifact is both invalidated and preserved. Fail.
17. **Receipt-only atomic claim**: the package omits the immutable raw-hash-verified base snapshot, applies against a stale base, changes another owner's artifact content, or changes a declared preserved Canon entry. Fail.

## Completion evidence

Both JSON files parse, both validator commands exit zero, positive fixtures pass, adversarial fixtures fail for their intended reason, every approved reference is independent and inspected, and the package never claims authority over identity, shot action, provider binding, video generation or post-production.
