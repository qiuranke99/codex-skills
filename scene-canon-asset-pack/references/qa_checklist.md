# Consistency QA Checklist

Run this checklist on every generated or regenerated machine asset, then run package-level cross-view checks. Record evidence and pass/fail per item; a hard-gate failure sets `repair_required`.

## 1. Source Fidelity

- Preserve every Source-Locked and Source-Corroborated element's form, count, position, orientation, and source state.
- Detect mirror/flip errors and left/right reversal.
- Do not promote estimated or completed content to source evidence.

## 2. Topology

- Verify doors, windows, roads, corridors, entries/exits, facade connections, landform/river/coast continuity, cosmic-system relations, and surreal topology rules.
- Verify reverse-direction relationships in both directions.

## 3. Scale

- Verify room dimensions, building height, openings, fixed furniture, terrain scale, ridge distance, horizon, celestial relative size, and multi-scale hierarchy.

## 4. Landmark Consistency

- Verify landmark position, direction, count, silhouette, distance, occlusion, and high/low-angle relation.

## 5. Material Identity

- Verify material classes, texture scale, base colors, and surface identity across views.
- Fail if source lighting color becomes a material color or if one surface changes material between views.

## 6. Fixed Content And Exclusions

- Verify fixed content remains present and oriented correctly.
- Fail new furniture, cups, plants, cloths, signs, vehicles, people, animals, boats, spacecraft, products, or celestial bodies unless approved.

## 7. High / Low Reveal

When applicable, inspect ceilings, floors, roofs, bases, furniture tops, valley height, coast slope, ring structure, and upper/lower volume layers. Fail hidden-region contradictions exposed only by angle change.

## 8. Loop Closure

- Verify bidirectional expansions converge.
- Return to the source direction and confirm the same scene, dimensions, landmarks, completion, materials, and orientation.

## 9. Duplicate View

- Fail near-identical views, crop-only changes, uniform camera height, or views with no new spatial information.

## 10. Content And Layout Contamination

- Fail text, titles, numbers, arrows, watermarks, borders, UI, collage, multi-grid, people, products, temporary props, and unrelated objects in machine assets.
- Confirm the overview board is derived from approved independent assets and is never treated as a machine plate.

## 11. Look Contamination

Run `look_contamination_checklist.md`. Fail both inherited cinematic look and accidental deletion of intrinsic emission or defining state.

## 12. Dimensions And Provenance

- Verify actual pixels from the returned/local file.
- Fail unverified dimension records or unsupported native-4K claims.
- Confirm the asset was independently generated and not cropped from a multi-panel source.

## 13. 4K Mapping

Run `4k_prompt_qa_checklist.md` after every asset passes visual QA. A regenerated asset invalidates its old prompt until remapped.

## Package Gate

Approve only when every required asset passes all applicable checks, no hard blocker remains inside the minimum-complete boundary, and the package validator exits zero. Keep assistant QA distinct from user or external production approval.
