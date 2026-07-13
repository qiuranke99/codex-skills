# High-Control AI TVC Production SOP

这是一套面向高质量 AI 视频广告的高控制生产流程。它把粗脚本逐层编译成可提交给第三方视频模型的全能参考生成包，而不是让模型从一段文字自由发挥。

## 1. 最终完成态

本 SOP 的终点是 **P2 Final Prompt Package**：每个生成单元都拥有经过验证的镜头语义、完整多模态参考绑定、全局导演规则、全局影调、镜头级影调状态、控制预演、目标节奏、Seedance 2.5-first 提示词、Seedance 2.0 兼容渲染和 provider payload manifest。

本 SOP 不包含：

- 实际调用第三方视频生成 API；
- 文生视频；
- 经典单图生视频；
- 首帧、尾帧、首尾帧或端点插值模式；
- 音乐、配乐、后期剪辑、调色或独立成片 QC；
- 宣称“一键自动出片”的运行编排器。

允许并鼓励把角色、产品、场景、影调图、故事板、关键帧和控制视频作为普通并行参考，统一送入 `omni_reference_to_video` / all-reference / multimodal reference-to-video 路径。

## GitHub release 前置门

GitHub `qiuranke99/codex-skills` 的 `main` 是 Windows/Mac 唯一跨机发布
权威。新项目、恢复项目和每个 0–10 阶段开始前，都必须运行当前不可变
snapshot 内的 OS-native `tools/release-control.ps1` / `tools/release-control.sh`
固定运行时入口执行 `check` 并要求 `ready_latest=true`；不得通过未验证的全局
Python 直接调用底层脚本。
本阶段把返回的 `release_commit` 写入 runtime/dependency lock；阶段内冻结该
commit。GitHub 更新、离线、验证失败、receipt/snapshot/discovery 漂移或
当前 Codex task 需要重启时必须停止，运行 `sync` 并从新 task 继续，绝不
调用旧 Skill 或混用两个 revision。

## 2. 六条不可妥协规则

1. **粗脚本不是缺陷。** 用户只需提供创意、写意画面、镜头表或部分时长。普通导演决策由系统推断并记录，不能退回给用户补专业术语。
2. **唯一 Project Canon。** 所有获批资产、版本、哈希、依赖和失效状态都登记到 `<PROJECT_ROOT>/00_project_canon/PROJECT_CANON_MANIFEST.json`；各阶段不得自建第二本 Canon。
3. **故事板 N=N。** 专业脚本有 N 个 Shot UID，就必须有 N 个独立故事板文件和 N 个有效审阅格。多宫格图只用于人审，不作为模型输入。
4. **全局影调三层锁。** 文本 Look Core、独立影调参考图和下游逐镜继承缺一不可。不能用一张漂亮参考图代替完整影调合同。
5. **生成单元不等于镜头。** Shot UID 数量由脚本决定；API 请求数由 P1 根据真实 provider 能力、参考预算和连续性决定。不得默认每镜三秒。
6. **所有返工只有一个责任 Owner。** 先修拥有事实的上游资产，再重建精确下游后代；不准靠提示词偷偷覆盖仍然有效的上游 Canon。

## 3. 0–11 完整节点

系统采用与流程图一致的 `0–11` 编号：0–10 是从素材摄取到 P2 的生产
节点，11 是用户审片与唯一 Owner 返工入口，不是独立 QC。Storyboard
节点 4 具有结构稿和最终稿两个明确审批子门，因此以下表格写作 4A/4B。

| 阶段 | Owner / Skill | 主要工具 | 输入 | 核心动作 | 输出 | 前进门 | 失败回路 |
|---|---|---|---|---|---|---|---|
| 0. 素材摄取与证据封存 | `ai-video-shot-script-director` | Codex、确定性文档提取器 | 创意、分镜表、DOCX/TXT/MD、产品事实、可选参考 | 保存原始字节和 hash；抽取文本、表格、镜号与时长；保留原始顺序和 supplied copy | Source Evidence、Extraction Report、输入清单 | 源文件可定位；抽取方法和输出 hash 可复核；不可读字段被局部隔离 | 文档不可读取 → 只阻塞受影响字段；Windows legacy DOC/RTF → 先确定性转 DOCX/TXT，保留原始文件 |
| 1. 专业镜头合同 | `ai-video-shot-script-director` | Codex、Shot validator | 节点 0 的证据与创意意图 | 保留创意模式；推断普通导演决策；冻结 Shot UID、时长、动作、机位、连续性、广告功能、Global Directing Grammar；初始化 Project Canon | Professional Shot Contract、可读版、Canon | 时长闭合；每镜可见动作和终态完整；无虚构 claim；validator 通过；用户批准 | 品牌方向或法务事实冲突 → 只请求唯一不可替代事实；其他普通导演缺口由系统完成 |
| 2. Canon 资产锁定 | 7 个窄域资产 Owner | Codex Image Generation、原始参考图、Owner validator | Shot Contract 的资产需求、角色/产品/包装/材质/场景参考 | 为每个资产选择唯一适用 Owner；生成、后验检查、批准；经 Owner bridge 写入 Canon | 角色、产品、包装、材质、场景 Canon 资产与记录 | 图片真实存在并经后验检查；Owner QA 通过；明确生产批准；Canon transition 通过 | 身份/几何/文字/材质证据冲突 → 回对应 Owner；复杂机制无专属 Owner → 仅阻塞该资产范围，不猜测结构 |
| 3. 全局影调锁定 | `ai-video-global-look-lock` | Codex Image Generation、Look references | Shot Contract、已批准身份资产、可选影调参考 | 建立 Look Core、必要 Look States、每镜 Delta；生成独立影调证明图；冻结完整全局影调块 | Global Look Contract、Look Reference Set、逐镜 State/Delta 映射 | 三层锁一致；每个 Shot UID 恰好一个 State；产品/肤色/材质边界明确；用户批准 | Core 错 → 全局返工；State 错 → 返对应 State；单镜偏差 → 只修 Delta |
| 4A. 故事板结构稿 | `ai-video-modular-storyboard` | Codex Image Generation | Shot Contract、必要 Canon 资产；可使用临时 Look | 每个 Shot UID 独立生成一个低成本全帧；验证构图、代表瞬间、eyeline、blocking、顺序和屏幕方向 | N 个 `structure_draft`、确定性人审板 | `脚本镜数 = 独立帧数 = 有效格数 = N`；用户确认镜头结构 | 改构图实现 → 只替换该帧；改镜头数量/顺序/时长 → 返回 Shot Contract |
| 4B. 故事板最终稿 | `ai-video-modular-storyboard` | Codex Image Generation、确定性 review-board compositor | 已批准结构稿、最终 Canon 资产、Global Look | 重建或严格晋升每个独立帧；继承身份、产品、场景、Look Core/State/Delta | N 个 `look_applied_final`、确定性人审板 | 每帧后验检查；逐帧 hash；无多宫格裁切；全局影调继承；用户批准 | 某帧失败 → 仅替换对应 Shot UID；全局事实错 → 回事实 Owner |
| 5. V1 Timing Animatic | `ai-video-timed-animatic-previs-director` | FFmpeg/ffprobe、确定性 2D animatic 或中性 3D blocking | Shot Contract、最终故事板 | 在整条广告绝对时间轴上锁定镜头边界、节奏、切点、粗运镜与 blocking | 无声 V1 MP4、timing map、媒体证据 | 从 0 开始、连续、终点等于总时长；章节边界一致；ffprobe 实测通过；用户批准 | 节奏/镜头意图错 → Shot Contract；静态构图错 → Storyboard；不要用关键帧补偿 |
| 6. K1 Core Keyframes | `ai-video-keyframe-continuity-pack` | Codex Image Generation | Shot Contract、最终故事板、Canon 资产、Global Look、V1 | 每镜至少一个生成级 anchor；为动作、液体、材质、产品状态增加最少必要锚点；建立状态账本 | K1 关键帧包、角色/产品/材质/动态状态账本 | 每个 Shot UID 至少一个批准锚点或严格晋升；提示词完整继承导演和影调块；用户批准 | 身份/状态错 → 对应资产 Owner 或 K1；时间锚点错 → V1；不得预先发明 Generation Unit ID |
| 7. P1 Generation Unit Preflight | `ai-video-omni-reference-prompt-director` `preflight` | Provider schema/capability evidence、Pillow、ffprobe | 完整 Canon 快照、Shot Contract、Global Look、Storyboard Final、V1、K1、Provider 能力证据 | 规划最少连续生成单元；逐单元分类全部 active Canon；预算直接参考、atlas 和未来 K2/V2；实测媒体约束 | P1 计划、模型/Provider 能力档案、证据快照 | Shot UID 完整有序覆盖；每项 active Canon 有决策；预算由证据推导；P1 validator 通过；用户批准 | Provider 缺必要模态 → 阻塞，不降级；单个 Shot UID 超限 → 返回 Shot Contract 拆成稳定镜头 |
| 8. K2 Boundary Supplement | `ai-video-keyframe-continuity-pack` | Codex Image Generation | 不可变 K1、已批准 P1 | 为相邻生成单元建立 handoff；只在 K1 不足时增加 boundary anchor | K2 Boundary Supplement 或 `single_generation_unit` 豁免 | 多单元边界逐一闭合；K2 不修改 K1 hash；用户批准 | Unit 计划变更 → P1 重做；边界状态事实错 → K1/对应资产 Owner |
| 9. V2 Control Previs | `ai-video-timed-animatic-previs-director` | 中性 2D/3D control-video 工具、FFmpeg/ffprobe | V1、K1、P1、K2、hash-bound provider capability snapshot | 每个多镜或 timing-sensitive 单元制作无声控制视频；锁定运镜、blocking、cut、物体和物理运动 | 每单元 V2 MP4、camera/blocking/physics tracks | 单元边界与 V1 完全一致；媒体实测满足 provider；视频无声且非成片；用户批准 | Provider 不支持 video reference → 回 P1 或更换经验证 provider；运动错 → 只修 V2 |
| 10. P2 Final Prompt Compile | `ai-video-omni-reference-prompt-director` `compile` | Pillow、ffprobe、Provider adapter | 新 Canon 编译快照、P1、K2、V2 和所有批准资产 | 构建 canonical IR；绑定全部相关非冲突参考；必要时无损 atlas；编译 2.5-first、2.0-aware 单元/逐镜修复提示词和 payload | P2 最终包、binding manifest、master/unit/repair prompts、payload、lockfile、反馈路由 | 所有上游 `user_approved`；完整继承 directing/look；实际媒体通过 provider 约束；无 T2V/I2V/端点降级；validator 通过 | 提示词/绑定错 → P2 revise；事实错 → 唯一上游 Owner；随机模型失败 → 同包重试后才做最小约束或单位调整 |
| 11. 用户审片与返工入口 | 用户 + 唯一 Owner 路由 | 第三方平台候选、冻结 P2 请求包 | 实际候选视频、provider profile、attachment mapping、用户观察 | 对照冻结请求包归因到 Shot UID / Unit / artifact / control role；只返回唯一 Owner | 接受画面，或可执行 upstream change request / Prompt revise | 用户明确接受，或返工 owner、范围和失效后代唯一确定 | 不设独立 QC Skill；只重建 owned artifact 和准确下游；Unit membership 变化返回 P1 |

## 4. 阶段依赖图

```text
粗脚本
  ↓
Professional Shot Contract
  ↓
Canon 资产 ─────┐
Global Look ────┼→ Storyboard Final → V1 → K1 → P1 → K2 → V2 → P2
Storyboard Structure ┘
                                                  ↓
                                           第三方平台生成
                                                  ↓
                                           用户观看并返工
```

严格的无环握手是：

```text
V1 → K1 → P1 → K2 → V2 → P2
```

- K1 不知道 Generation Unit ID。
- P1 是 Generation Unit 的唯一 Owner。
- K2 只消费已经冻结的 P1。
- V2 消费 P1 与 K2，不改变镜头事实。
- P2 消费完整链路，不重新发明资产或运动事实。

## 5. 从粗脚本开始时系统必须推断什么

以下缺失不能成为停工理由：

- 镜头高度、角度、景别与 lens intent；
- 主体 placement、blocking、screen direction、eyeline；
- 每镜一个主要运镜，包括 `locked_off`；
- focus behavior、动作准备/发生/结束状态；
- cut motivation、continuity in/out；
- 写意情绪对应的可见表演；
- 低风险、可逆的液体/衣物/头发/手部行为。

系统必须把这些内容写入 inference ledger，并注明理由、置信度、来源依据和可逆性。

系统不能推断为事实的内容：

- 产品功效、配方、测试数据、认证、法规承诺；
- 精确包装文字、商标细节、二维码、条形码；
- 未被参考证明的机械结构、阀门、泵体、隐藏管道或容器内部构造；
- 相互排斥的品牌方向或会改变作品身份的重大创意决策。

对于写意品牌片，用户没有提供“干皮逻辑”或完整产品使用流程并不构成阻塞。除非源脚本明确要求功能演示，否则不得强迫其变成功能说明片。

## 6. 全局影调如何贯穿全部镜头

全局影调不是单独的参考图，而是以下三层共同构成的版本化合同：

1. `GLOBAL_LOOK_PROMPT_FULL`：全片不变的色彩关系、光源层级、反差、黑位、高光 roll-off、肤色、材质响应、光学纹理、颗粒和氛围规则。
2. `LOOK_STATE`：同一 Look Core 在不同场景、时段、曝光或 practical-light 条件下的合法状态。
3. `SHOT_LOOK_DELTA`：仅解决单镜必要差异，不能重写 Core 或 State。

继承规则：

- 每个 `look_applied_final` 故事板提示词必须逐字注入 Core → State → Delta；
- 每个独立关键帧提示词必须逐字注入 Core → State → Delta；
- 每个 P2 generation-unit prompt 和 shot repair prompt 必须逐字注入完整 Global Directing 与 Core → State → Delta；
- V1/V2 是中性时间与运动控制，不承担最终影调，不应被误当作 Look reference；
- 改 Core 会使所有 look-applied 下游资产失效；改 State 只影响使用该 State 的镜头；改 Delta 只影响指定 Shot UID。

## 7. 故事板的正确形态

正确：

```text
S001.png
S002.png
S003.png
...
SN.png
```

然后通过确定性排版生成一张人类审阅用多宫格图。故事板多宫格图的标签、镜号、时长和注释都位于图像格外，不进入模型参考。

错误：

- 让图像模型一次生成 N 宫格，再裁切；
- 为了让 review board 更漂亮而重生成所有镜头；
- 修改一个镜头时破坏其他镜头文件或 hash；
- 把人审多宫格替代独立帧输入视频模型。

若只改 S005 和 S008，就只替换这两个独立文件，再确定性重建 review board。若改镜头顺序、数量、时长、合并或拆分，必须先回到 Shot Contract。

## 8. Generation Unit 与节奏控制

一个 15 秒生成请求可以包含多个镜头，但每镜时长来自 Shot Contract 和 V1，不是来自固定模板。P1 只在以下事实交集内规划单元：

- provider 已验证的最大时长；
- 图片、视频、音频及总引用预算；
- MIME、container、codec、像素、比例、帧率、文件大小和 audio-track policy；
- 镜头连续性和完整 Shot UID 边界；
- V2 control-video 覆盖；
- 身份、材质和运动复杂度。

不得把一个 Shot UID 从内部切开来适配 provider。如果一个镜头本身超过真实限制，先由 Shot Script Director 把它改写为多个稳定 Shot UID，保持总时长和意图，再重建精确下游。

目标时长是导演合同；生成模型对秒级边界的服从不是数学保证。V1 + V2 + P2 target windows 提供当前流程内最高控制力，但仍需由用户观看实际结果并决定是否返工。

## 9. Provider capability snapshot

P1/V2/P2 不能从模型名称或宣传页面猜能力。每个真实 provider surface 都需要本地、可哈希、可复核的能力证据，至少包含：

- provider、endpoint/surface、model ID、backend binding、采集时间与证据来源；
- 唯一合法 generation mode 是否为 `omni_reference_to_video`；
- 支持的 image/video/audio/text modalities；
- 每种模态的数量和总预算；
- duration、bytes、width、height、aspect ratio、fps；
- media type、container、codec、audio-track policy；
- 未知字段和不能验证的宣传性声明。

Seedance 2.5 在本仓库中首先是 `seedance_2_5_forward_compatible` 语义目标。除非所选 provider 给出可验证 runtime evidence，不得把“50 个多模态输入”“30 秒”等预览或用户转述当成 payload 预算。

本仓库包含 Seedance 2.0 documented-backend baseline，但最终仍必须与实际第三方 provider surface 取更严格交集；第三方平台可能只暴露更少能力。

## 10. 两种执行路径

### 高控制路径（默认）

适合高端 TVC、人物身份敏感、包装文字敏感、玻璃/液体/反光材质、复杂动作、多场景、多 Look State 或多生成单元项目。

- 完整执行 0–11 全部节点（含 4A/4B 两个故事板审批子门与节点 11 用户返工入口）；
- 每个视觉资产独立生成并在后续回合检查；
- 对复杂动作、材质状态和 unit handoff 增加必要 K1/K2；
- 每个多镜或 timing-sensitive 单元制作 V2；
- 每个阶段在下游消费前获得明确用户批准。

### 效率路径（不是低控制捷径）

适合身份资产已充分、场景较少、单一 Look Core、动作简单、provider 可容纳一个完整生成单元的广告。

- 仍保留 Shot Contract、N 个独立故事板、Global Look、V1、K1、P1、V2 和 P2；
- 最终故事板帧若严格通过全部生成级检查，可晋升为主关键帧；
- K1 每镜从一个主 anchor 起步，仅对真实状态风险加锚点；
- 单 Generation Unit 使用 K2 的 `single_generation_unit` 豁免；
- 只在 provider 预算需要时构建 atlas，不主动凑满参考数量；
- 单个静态、近乎无运动且全项目只有一镜时，才可使用合同允许的 V1/V2 exemption。

“一次生成 15 秒多镜”只是 generation-unit 策略，不会取消故事板 N=N、V1 节奏、K1 连续性或 V2 运动控制。

## 11. 结束条件

P2 可以交付给第三方平台，仅当：

- 所有上游事实均为 `user_approved`、hash-valid、非 stale；
- P1、K2、V2 与 P2 的 Shot UID、unit membership 和依赖完全一致；
- 每个相关且不冲突的 Canon 资产都被直接绑定、通过确定性 atlas 运送，或有可验证的非相关理由；
- 每个 generation-unit prompt 和 repair prompt 都完整继承 Global Directing 与 Global Look；
- 所有实际媒体文件通过当前 provider 上传约束实测；
- provider payload 递归拒绝 T2V、单图 I2V 和端点帧字段；
- 阶段 validator、Canon transition 与 dependency lock 全部通过；
- 文档明确说明：结构通过不等于模型一定生成成功，也不等于用户已经接受成片。
