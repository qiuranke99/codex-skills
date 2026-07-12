# Feedback Routing Contract

User review feedback is an input to `revise`; it is not an independent video-QC process.

## Sole-Owner Routing

| Observed user feedback | Owner | This Skill action |
|---|---|---|
| story, shot count/order, target duration, narrative/advertising function | `ai-video-shot-script-director` | issue upstream request |
| face, body, wardrobe, product geometry, exact label evidence, material construction, scene canon | corresponding asset skill | issue upstream request |
| global light, color, contrast, texture, grain, highlight/black behavior | `ai-video-global-look-lock` | issue upstream request |
| approved normative shot size, camera height/angle, composition principle, or placement target is being changed | `ai-video-shot-script-director` | issue upstream request |
| a representative still fails to realize the approved static framing, composition, camera position, or subject placement | `ai-video-modular-storyboard` | issue upstream request |
| pose, visible identity/product/material state, shot continuity | `ai-video-keyframe-continuity-pack` | issue upstream request |
| time-varying camera path, blocking, speed, cut realization, or physical motion timing | `ai-video-timed-animatic-previs-director` | issue upstream request |
| alias misbinding, prompt ambiguity, unit split, reference budget, provider serialization | `ai-video-omni-reference-prompt-director` | revise directly |
| all controls correct but stochastic model failure | this Skill | retry exact package, then minimal constraint change, shorter unit, or verified provider change |

## Structured Route Record

```json
{
  "feedback_id": "FB001",
  "user_feedback": "S005 product label turns away from camera",
  "affected_shot_uids": ["S005"],
  "affected_artifact_ids": ["PRODUCT_PACKAGING_CANON_001"],
  "affected_control_roles": ["label_copy"],
  "diagnosis_scope": "identity_product_material_scene_canon",
  "evidence_comparison": ["the provider package bound the correct label asset, while the approved product keyframe already shows the wrong facing state"],
  "owner_skill": "packaging-product-identity-label-lock-board",
  "action": "issue_upstream_change_request",
  "owned_diff": null,
  "upstream_change_request": {
    "request_id": "CR001",
    "target_owner_skill": "packaging-product-identity-label-lock-board",
    "affected_shot_uids": ["S005"],
    "affected_artifact_ids": ["PRODUCT_PACKAGING_CANON_001"],
    "affected_control_roles": ["label_copy"],
    "conflict": "approved label-facing state is inconsistent with the required shot state",
    "required_resolution": "publish a corrected owner-side Canon asset revision"
  },
  "invalidated_artifact_ids": [],
  "unaffected_artifact_hashes": {}
}
```

Every upstream route names exact `affected_artifact_ids` and at least one `affected_control_roles` entry. Roles must be a precise subset of the named artifacts' authorized role union; the nested request repeats identical artifact, role, and Shot scopes. Prompt-owned serialization fixes and stochastic retries use an empty role list. Every artifact must resolve in validated Canon inventory and share `owner_skill`; choosing any installed owner is invalid. When a keyframe itself is wrong, route to Keyframe Pack and name its exact artifact and semantic role.

For camera/framing feedback, test these three cases explicitly:

1. the user changes the already approved low-angle intention → Shot Script Director;
2. the storyboard frame is high-angle although the Shot Contract remains low-angle → Modular Storyboard;
3. the start frame is correct but the moving camera rises along the wrong path → Timed Animatic/Previs Director.

## Revision Discipline

- Change the smallest owned surface.
- Preserve unaffected unit/repair prompt bytes when global blocks did not change.
- Create new SemVer artifacts and hashes.
- Record exact before/after values and reasons.
- Never patch prompt text to contradict a still-approved upstream artifact.
- Never call the route record “QC approval.” The user remains the footage acceptance authority.
