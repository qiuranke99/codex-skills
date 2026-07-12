# Seedance Prompt Rendering Template

Use the complete structure below for every generation unit. Do not omit a section because it repeats another unit.

```text
[生成任务与输出规格]
使用全能参考/多模态 reference-to-video 生成 <unit duration> 的连续广告视频单元。
镜头范围：<ordered shot UIDs>。画幅、输出和 provider 参数：<verified values only>。

[素材及控制权映射]
<provider alias> = <semantic subject/reference>, controls only <role/scope>.
...

[主要主体]
<stable subject definitions and identity/product locks>

[场景与环境初始状态]
<scene canon, spatial state, initial object/material state>

[情绪与广告目标的可见表现]
<visible posture, gaze, breath, hand action, product attention; no abstract-only emotion>

[全局导演语法｜原文逐字继承]
<GLOBAL_DIRECTING_GRAMMAR exact bytes>

[全局影调｜原文逐字继承]
<GLOBAL_LOOK_PROMPT_FULL exact bytes>

[全局连续性与禁止项]
<identity, wardrobe, product, label, material, scene, screen-direction, no invented text/claims>

[分段镜头]
S001｜目标时间窗 <canonical target>｜广告功能 <function>
主体动作与可见表演：...
景别、机位与单一主要运镜：...
走位、空间和物质状态变化：...
结束状态与下一镜衔接：...
LOOK_STATE_ID：<exact approved state ID>
LOOK_STATE_PROMPT_FULL：<exact approved State block bytes>
LOOK_STATE_REFERENCES：<exact approved reference IDs/version/hash>
SHOT_LOOK_DELTA：<structured legal delta plus exact rendered delta, or explicit none>
对白/旁白：<source-backed text plus model_spoken | external_overlay_handoff | prohibited_model_text>
上屏文字：<source-backed text plus external_overlay_handoff | prohibited_model_text>
CLAIM_PROVENANCE：<claim ID, source IDs, allowed/prohibited boundary>

S002｜...

[稳定与负面约束]
<unit-specific constraints; no conflicting camera or asset instructions>
```

## Seedance 2.5-First Render

- Keep explicit target time windows and full role bindings.
- Preserve the full structured sequence and cross-shot continuity.
- Label the file/header `forward-compatible semantic target` until provider runtime verification exists.
- Never write a preview capacity claim as an active payload limit.

## Seedance 2.0 Render

- Keep exact time windows in canonical IR and payload metadata.
- Render model-facing shots in strict order with relative pacing when exact seconds are not reliably honored.
- Keep each unit at or below 15 seconds.
- Keep each unit at or below 9 images, 3 videos, and 3 audio files, further reduced by provider limits.
- Define subjects before action sentences; translate provider aliases to semantic labels.
- Use one primary camera movement per shot.

## Repair Prompt Template

Each shot repair prompt is self-contained:

```text
Repair target: <shot_uid>; preserve every approved upstream fact not listed in change_request.
Complete reference mapping: <all shot-relevant aliases and roles>.
GLOBAL_DIRECTING_GRAMMAR: <exact full block>.
GLOBAL_LOOK_PROMPT_FULL: <exact full block>.
LOOK_STATE_ID: <exact approved State ID>.
LOOK_STATE_PROMPT_FULL: <exact approved State block>.
LOOK_STATE_REFERENCES: <exact approved reference identities>.
SHOT_LOOK_DELTA: <exact legal delta block>.
Shot contract: <complete action/camera/blocking/end-state/copy/claim block>.
Repair instruction: <prompt-owned correction only>.
Continuity in/out: <exact boundary facts>.
Forbidden changes: <identity/product/material/scene/look/story changes>.
```

Do not write “same as master prompt,” “keep previous style,” or “fix shot 5” without full context.

The mandatory look order in every unit and repair prompt is:

```text
GLOBAL_LOOK_PROMPT_FULL
→ assigned LOOK_STATE_PROMPT_FULL and LOOK_STATE_REFERENCES
→ SHOT_LOOK_DELTA
```

The State block is not optional even when several adjacent shots share one State. The Delta must not restate or contradict the Core or State.
