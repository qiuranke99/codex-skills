# Codex 使用指令集

本文件提供可以直接复制给 Codex 的指令。它们用于驱动阶段化生产，不代表一个自动调用第三方视频 API 的一键编排器。

## 1. 开始前只替换这些变量

```text
<SYSTEM_ROOT>           release_control.py check 返回的 active_system_root；禁止填写 authoring checkout
<PROJECT_ROOT>          项目绝对路径
<SOURCE_SCRIPT>         粗脚本、分镜表或创意文件的绝对路径
<REFERENCE_ROOT>        原始角色、产品、包装、场景、影调参考所在目录
<TARGET_DURATION>       目标总时长；未知可写“从源脚本提取”
<ASPECT_RATIO>          例如 16:9 或 9:16
<PROVIDER_EVIDENCE>     当前第三方平台/模型能力证据文件；尚未获得时写“暂缺，P1 前补齐”
<USER_NOTES>            本次额外创意约束、不可改镜头、已确认 copy 等
```

Windows 示例：

```text
<SYSTEM_ROOT> = C:\Users\you\.codex\skills\.high-control-ai-tvc-production-system-releases\releases\<GITHUB_OID>\repo\high-control-ai-tvc
<PROJECT_ROOT> = C:\AI-TVC\bath-oil
<SOURCE_SCRIPT> = C:\AI-TVC\bath-oil\01_sources\script\original\rough-shot-script.docx
```

macOS 示例：

```text
<SYSTEM_ROOT> = /Users/your-name/.agents/skills/.high-control-ai-tvc-production-system-releases/releases/<GITHUB_OID>/repo/high-control-ai-tvc
<PROJECT_ROOT> = /Users/your-name/AI-TVC-Projects/bath-oil
<SOURCE_SCRIPT> = /Users/your-name/AI-TVC-Projects/bath-oil/01_sources/script/original/rough-shot-script.docx
```

路径中有空格时始终保留完整绝对路径，并让 Codex 在命令层正确加引号。Windows 旧 `.doc`/`.rtf` 需要先通过 Word 或受信任转换器保存为 `.docx`；不要让 Codex猜测无法读取的二进制文本。

## 2. 全流程 Master Prompt

把下面整段交给 Codex。它会从粗脚本开始，推进到每个真实审批门，而不是要求用户先写专业导演脚本。

```text
请使用本仓库的 High-Control AI TVC Production SOP，为下列项目建立并执行高控制全能参考工作流。

PROJECT_ROOT: <PROJECT_ROOT>
SYSTEM_ROOT: <SYSTEM_ROOT>
SOURCE_SCRIPT: <SOURCE_SCRIPT>
REFERENCE_ROOT: <REFERENCE_ROOT>
TARGET_DURATION: <TARGET_DURATION>
ASPECT_RATIO: <ASPECT_RATIO>
PROVIDER_EVIDENCE: <PROVIDER_EVIDENCE>
USER_NOTES: <USER_NOTES>

目标：从用户能够提供的粗脚本开始，最终交付 P2 Final Prompt Package。P2 应包含完整 Canon inventory、generation-unit 计划、全部相关非冲突参考绑定、Seedance 2.5-first forward-compatible master/unit/repair prompts、Seedance 2.0 capability-aware render、provider payload manifest、dependency lockfile 和 feedback route。

严格执行以下规则：

1. 在读取任何生产 Skill 或写任何 artifact 前，先运行 `<SYSTEM_ROOT>/tools/release_control.py check --project-root <PROJECT_ROOT> --format json`。只有 `ready_latest=true` 才能继续，并把返回的 `release_commit` 写入本阶段 runtime/dependency lock；若远端更新、离线、snapshot/receipt/discovery 漂移或提示 `PROCESS_RESTART_REQUIRED`，立即停止，运行 `sync` 后打开新的 Codex task，绝不回退旧 release。随后完整读取 <SYSTEM_ROOT>/docs/SOP.md、<SYSTEM_ROOT>/docs/TOOLS_INPUTS_OUTPUTS.md、<SYSTEM_ROOT>/docs/REVISION_AND_APPROVAL.md、<SYSTEM_ROOT>/docs/PROJECT_STRUCTURE.md，以及当前阶段 Skill 的 SKILL.md 和其要求的 references。若 <SYSTEM_ROOT> 不存在或不含 SUITE_MANIFEST.json，报告安装 blocker；不得从聊天记忆或本机 authoring checkout 伪造 SOP。
2. 使用唯一的 <PROJECT_ROOT>/00_project_canon/PROJECT_CANON_MANIFEST.json。不得建立第二本 Canon，也不得让生产 artifact 反向依赖 Canon。
3. 不得因为脚本缺少专业机位、运镜、blocking、continuity、产品使用逻辑或功能说明而停工。保留源创意模式，自主推断普通导演决策并写入 inference ledger；写意品牌片不得被强改成功能演示片。
4. 不得发明产品功效、配方、测试数据、认证、法规 claim、精确包装 copy 或未被证据支持的机械结构。只隔离真正不可替代的 blocker，继续完成所有不受影响的工作。
5. 依次执行 0–10 完整仓库生产节点：
   Intake → Shot Contract → Canon Assets → Global Look → Storyboard Structure → Storyboard Final → V1 → K1 → P1 → K2 → V2 → P2。Storyboard Structure 与 Final 是同一阶段的两个审批子门。节点 11 User Review 只在我已于仓库外部完成第三方 Omni 生成并提供候选视频后启用；它属于外部返工回路，不是独立 QC，也不是本次 P2 交付前置条件。
6. 故事板必须保持 script_shot_count = independent_storyboard_frame_count = rendered_valid_cell_count = N。每镜独立生成；多宫格只用于人审，绝不作为模型输入。
7. 全局影调必须是三层锁：GLOBAL_LOOK_PROMPT_FULL + 独立 Look Reference Set + 下游继承。每个最终故事板、关键帧、generation-unit prompt 和 repair prompt逐字继承 Global Directing、Look Core、assigned Look State 和 legal Shot Delta。V1/V2 保持中性，不承担最终影调。
8. 只允许 omni_reference_to_video / all-reference / multimodal reference-to-video。禁止 text-to-video、classic standalone single-image-to-video、first/last/start/end/endpoint-frame 和 interpolation。普通图片作为 Omni 并行参考是允许且必要的。
9. P1 是 Generation Unit Map 的唯一 Owner。不得默认每镜 3 秒，不得把 Shot UID 从内部拆开。P1 必须读取并分类完整 active Canon，使用 hash-bound provider capability evidence 规划最少连续单元和参考预算。
10. Seedance 2.5 只作为 forward-compatible semantic target，除非 provider runtime evidence 验证其真实限制。不得把预览、传闻或用户转述的参考数量/时长当成 payload 预算。Seedance 2.0 baseline 也必须与当前第三方 provider surface 取更严格交集。
11. 所有图像生成前先冻结提示词和 sidecar；图像调用必须是该回合最后动作。下一回合检查真实输出、尺寸和 hash 后才能批准，不能把未检查的图像视为完成。
12. 每阶段先生产真实 artifact，再运行该 Skill 的 validator 和 Project Canon transition。validator 只证明结构与证据闭合，不代表用户审美批准、法律批准或 provider 一定服从。
13. 只有用户明确批准才能写 user_approved。遇到下游要求 user_approved 时暂停，给我展示本阶段关键资产、变更范围、验证结果、风险与明确的批准对象；不要替我批准。
14. 不调用第三方视频生成 API；不做音乐、剪辑、调色或独立成片 QC。终点为经过验证的 P2 包。
15. 若发现问题，先按 sole-owner 路由修复唯一上游事实，再重建精确的 downstream descendants。不要靠 P2 提示词覆盖上游错误。
16. 每次从用户批准暂停恢复到下一阶段时，重新运行同一个 release gate。一个原子阶段内冻结同一 `release_commit`；GitHub `main` 变化时先停止并迁移，禁止同一 Canon transaction 混用两个 Skill revision。

开始时先：
- 检查 Skill 是否可发现、Python/Pillow/FFmpeg/ffprobe 是否可用；
- validator 必须使用 release receipt `validation.python_executable` 对应的已验证运行时，或由 `AI_TVC_PYTHON` 显式指定的同版本运行时；若不存在或版本不合格，报告 runtime blocker，不得悄悄改用不受控环境；
- 检查源文件实际可读；
- 建立项目目录和 source inventory；
- 执行 $ai-video-shot-script-director；
- 持续推进到第一个真实用户批准门，再暂停并交付可核验 artifact。
```

## 3. 阶段续跑 Prompt

Codex 每次暂停等待批准后，使用这段继续：

```text
我批准以下明确对象进入下游：<ARTIFACT_IDS / SHOT_UIDS / VERSION / HASH 或人类可读名称>。

请先运行 <SYSTEM_ROOT>/tools/release_control.py check --project-root <PROJECT_ROOT> --format json，并要求 ready_latest=true；若更新则先迁移并打开新 task。然后把批准证据写入对应 Owner 合同并验证 Canon transition，读取 <PROJECT_ROOT> 的完整 Project Canon，确认没有 stale、blocked、hash drift 或未完成 transaction。按照 <SYSTEM_ROOT>/docs/SOP.md 从当前阶段继续到下一个真实用户批准门。不要跳阶段，不要重新生成未受影响资产，不要调用第三方视频 API。
```

若只是允许使用 `assistant_validated` 结果做预览，不是生产批准：

```text
这些资产只获准用于明确标记的 working preview，不是 user_approved，也不能产生可执行 final payload。请保持 approval_status 诚实，并在下游首次要求生产批准时停下。
```

## 4. 单阶段 Prompt

### 4.1 粗脚本 → Professional Shot Contract

```text
Use $ai-video-shot-script-director to upgrade <SOURCE_SCRIPT> into a director-grade Professional Shot Contract under <PROJECT_ROOT>.

保留源脚本的写意/叙事/功能模式。自主补齐普通导演决策、目标时间、可见动作、机位、一个主要运镜、blocking、cut、continuity、广告功能、资产需求、keyframe/previs needs。不要要求我补专业导演语言，不要因缺少产品使用逻辑而停工，不要发明 claims 或 exact copy。初始化唯一 Project Canon，运行 validator，然后交付我需要批准的镜头合同。
```

### 4.2 Canon 资产锁定

```text
读取已批准 Shot Contract 的 asset_requirement_map 和 <REFERENCE_ROOT>。为每项资产选择且仅选择一个正确 Owner：
- 角色初选：$character-casting-lock-board；默认不是终端 Canon；
- 完整终端角色：$character-final-lock-board；
- 单脸终端角色：$single-face-character-lock-board；
- 普通不透明产品：$multi-angle-product-identity-lock-board；
- 标签/文字优先包装：$packaging-product-identity-label-lock-board；
- 玻璃、透明、液体、反光、磨砂或材质敏感产品：$material-sensitive-product-master-asset-board；
- 场景与空间：$scene-canon-asset-pack。

不得为同一 asset_key 保留两个终端角色 Authority。按各 Owner 原始视觉工作流生成并在下一回合检查真实图像；只有显式生产批准后才经 fixed-owner Canon bridge 注册。不要让 Prompt Director代替资产 Owner 导出 Canon。
```

### 4.3 Global Look

```text
Use $ai-video-global-look-lock with the approved Shot Contract, all approved identity assets, and <LOOK_REFERENCES>.

建立完整 Look Core、最少必要 Look States、逐镜 Shot Deltas 和独立 Look Reference Set。保护产品固有颜色、材质、包装事实和肤色。冻结 GLOBAL_LOOK_PROMPT_FULL、State blocks 和 deterministic Delta blocks，证明每个 Shot UID 恰好分配一个 State。不要用一张 mood image 代替三层锁。运行 validator 后展示批准对象。
```

### 4.4 Storyboard Structure

```text
Use $ai-video-modular-storyboard to create structure_draft for every stable Shot UID in the approved Shot Contract.

必须一镜一文件，N 镜 = N 个独立全帧。只审代表瞬间、构图、机位、placement、blocking、eyeline、screen direction、镜头顺序和节奏可读性。生成确定性人审板，但标记 is_model_input:false。某帧失败只替换该 Shot UID；镜头重排/增删/拆并必须路由回 Shot Contract。
```

### 4.5 Storyboard Final

```text
继续使用 $ai-video-modular-storyboard，将已批准结构稿重建或严格晋升为 look_applied_final。

每帧绑定获批角色/产品/包装/材质/场景资产，并逐字注入 Global Directing、GLOBAL_LOOK_PROMPT_FULL、assigned LOOK_STATE、resolved Look Reference artifact IDs 和 legal SHOT_LOOK_DELTA。每次图像生成后在下一回合做实际视觉检查、尺寸与 hash 验证。只从独立帧确定性重建人审板。
```

### 4.6 V1 Timing Animatic

```text
Use $ai-video-timed-animatic-previs-director in timing_animatic_v1 mode with the approved Shot Contract and Storyboard Final.

建立整条广告的绝对时间线，不采用每镜固定 3 秒。锁定 Shot UID 顺序、开始/结束、cut、粗运镜、blocking、动作 entry/beat/exit。输出无声、provider-neutral、non-final V1，使用 ffprobe 实测 duration、视频流、零音频流、帧数和 Shot chapters。节奏不对时路由回 Shot Contract/Storyboard，不让 K1 补偿。
```

### 4.7 K1 Core Keyframes

```text
Use $ai-video-keyframe-continuity-pack in core_keyframes mode.

为每个 Shot UID 建立至少一个 generation-ready Omni reference anchor，并只在动作、液体、材质、产品状态或复杂 blocking 需要时增加锚点。先建立 character/product/material/dynamic ledgers，再生成独立全帧。关键帧不是 start/end frame。K1 不得包含 Generation Unit ID。每个提示词完整继承 approved authorities 和 Global Look。
```

### 4.8 P1 Generation Unit Preflight

```text
Use $ai-video-omni-reference-prompt-director in preflight mode.

读取完整 active Project Canon 与 <PROVIDER_EVIDENCE>，逐个 Generation Unit 分类每一个 active artifact；规划最少连续 units、直接绑定、planned atlas、future K2 和每个多镜/timing-sensitive unit 的 V2 video。单位只能在完整 Shot UID 之间切分。不得从模型名称猜 runtime 能力；不得产出 final prompt 或 executable payload。运行独立 P1 validator 后展示 unit map、预算、证据和 blockers。
```

### 4.9 K2 Boundary Supplement

```text
Use $ai-video-keyframe-continuity-pack in boundary_supplement mode with the immutable K1 and approved P1.

若只有一个 Generation Unit，写 single_generation_unit exemption。若有多个 unit，为每对相邻边界建立一个 handoff record；先复用 K1，只有确有控制缺口时才生成 boundary_handoff anchor。不得修改 K1 hash，不得在 Shot UID 内建立隐藏切分。
```

### 4.10 V2 Control Previs

```text
Use $ai-video-timed-animatic-previs-director in control_previs_v2 mode with approved V1, K1, P1 and K2.

先验证 hash-bound provider-runtime-capability-evidence，确认 multimodal video reference 可用。每个多镜或 timing-sensitive unit 生成一个无声 control_reference_video，精确继承 V1 边界并锁定 camera trajectory、blocking、cut 和必要的 liquid/cloth/hair/rigid-object tracks。V2 保持中性，不拥有 identity、product、label 或 look。使用 ffprobe 和 provider constraints 实测每个文件。
```

### 4.11 P2 Final Compile

```text
Use $ai-video-omni-reference-prompt-director in compile mode with the approved P1, K2, V2 and current complete Project Canon.

重新冻结 compile-time Canon snapshot。构建 canonical IR；为每个 unit 绑定全部相关非冲突 authorities；容量不足时先安全拆 unit，再移除真正 irrelevant/superseded 项，再考虑 deterministic no-resize atlas，绝不丢失 required control。输出 Seedance 2.5-first forward-compatible master/unit/shot-repair prompts、Seedance 2.0 capability-aware render、binding manifest、provider payload、capacity report、feedback route 和 dependency lockfile。每个 unit/repair prompt逐字重复 Global Directing 和 Global Look。递归拒绝 T2V、single-image I2V 和 endpoint-frame 字段。运行 final validator，但不要调用视频 API。
```

## 5. 用户看完生成视频后的返工 Prompt

### 通用诊断

```text
这是我对第三方平台生成结果的观察：<FEEDBACK>。
受影响镜头：<SHOT_UIDS 或“请从画面定位”>。
本次使用的 P2 package：<PACKAGE_PATH / VERSION>。

不要建立独立 QC 阶段。请把实际结果与冻结的 P2 request package、上游 Canon 和对应 control evidence 比较，生成一个 sole-owner feedback route。先判断问题属于 Shot Contract、某一 Canon asset owner、Global Look、Storyboard、K1/K2、V1/V2，还是 Prompt Director 自己。只修唯一 Owner 的最小事实表面，创建新版本/hash，标记精确 downstream descendants stale，再重建到 P2。不要通过提示词覆盖仍然获批的上游错误。
```

### 仅提示词/绑定问题

```text
Use $ai-video-omni-reference-prompt-director in revise mode. 这是 prompt ambiguity / alias binding / reference budget / provider serialization 问题：<FEEDBACK>。

保留全部获批上游事实；加载 previous IR、previous dependency lockfile 和 previous package hash。只修改受影响 unit/binding/repair prompt，输出 machine-readable diff，证明 unchanged outputs byte-stable。若证据显示问题实际属于上游，停止 Prompt patch 并输出精确 upstream_change_request。
```

### 全局影调问题

```text
生成结果在 <SHOT_UIDS> 出现以下影调问题：<FEEDBACK>。请先判定是 Look Core、某个 LOOK_STATE 还是 SHOT_LOOK_DELTA 的责任。

Use $ai-video-global-look-lock for the smallest legal revision. 不要改变产品固有颜色、材质或肤色身份。更新受影响视觉证明和 exact prompt blocks，标记精确 Storyboard/Keyframe/P2 descendants stale，再重建至 P2。Core revision 才允许全局失效。
```

### 节奏、运镜或物理运动问题

```text
生成结果在 <SHOT_UIDS / GENERATION_UNIT_IDS> 出现以下动态问题：<FEEDBACK>。

如果目标镜头时长、顺序或规范性运镜意图需要改变，路由给 $ai-video-shot-script-director；如果意图不变但时间路径、blocking、cut realization 或液体/衣物/头发/物体运动实现错误，使用 $ai-video-timed-animatic-previs-director 修复 V1 或 V2。只失效受影响 K1 time anchors、P1/K2/V2/P2 descendants，然后重建。
```

### 单个故事板或关键帧问题

```text
问题：<FEEDBACK>，受影响 Shot UID：<SHOT_UID>。

若批准的静态构图/placement 没被正确画出，使用 $ai-video-modular-storyboard 只替换该 Shot UID；若构图正确但 pose、product/material state 或 continuity anchor 错，使用 $ai-video-keyframe-continuity-pack 只重建该 shot 的 stale anchors。保留所有不受影响文件和 hash，随后重建精确 V2/P2 descendants。
```

## 6. 恢复中断或换电脑

```text
请恢复 <PROJECT_ROOT> 的 High-Control AI TVC 工作流。SYSTEM_ROOT: <SYSTEM_ROOT>。先运行 release check 并要求 GitHub main 与本阶段 release 一致；不一致时停止、sync、迁移并打开新 task。

不要依赖聊天记忆。先读取 <SYSTEM_ROOT>/docs、完整 PROJECT_CANON_MANIFEST、所有 active artifact records、PENDING_PROJECT_CANON_TRANSACTION.json（若存在）、最近一次 package validators 和 manifest receipts。验证实际文件 hash 与 Canon 一致，识别最后一个真实通过且已获所需批准的阶段、所有 stale/blocked artifacts 和唯一未完成 gate。若存在已提交但缺 receipt 的 transaction，按 Skill 合同从不可变证据恢复；若 transaction 仅 prepared，禁止其他 Canon writer 越过。然后从唯一合法下一阶段继续，不重做 byte-identical 已批准资产。
```
