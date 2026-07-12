# 审批、返工与失效传播

## 1. 谁负责批准什么

系统有三种完全不同的判断，不能互相代替：

1. **Validator**：证明 JSON、文件、hash、依赖、时长、媒体规格和合同结构闭合。
2. **Assistant visual/reasoning QA**：证明 Codex 已检查真实输出是否符合当前 Owner 合同。
3. **User approval**：用户决定该版本是否可进入生产下游。

只有用户明确表达批准，才能把 artifact 设置为 `user_approved`。validator success 不能证明：

- 用户审美已经满意；
- 产品 claim 或 exact copy 已获法律许可；
- 外部 provider 会逐秒服从控制；
- 最终生成视频已经可用。

## 2. 状态机

```text
draft
  ↓ producer completes + validator passes
assistant_validated
  ↓ explicit user approval
user_approved
  ↓ upstream fact or dependency changes
stale

blocked = 唯一不可替代条件缺失，且无法在不改变作品身份/真实性/合法生成路径的前提下绕过
```

规则：

- `draft` 可以没有最终 hash；其他状态必须符合各 Owner 的 hash 合同。
- `stale` 必须填写精确 `stale_reason`。
- `blocked` 只隔离受影响 Shot UID、asset 或 generation unit；所有无关工作继续推进。
- `assistant_validated` 可以用于明确标记的 working preview，但最终 P2 executable payload 的上游必须全部 `user_approved`。
- 批准永远绑定具体 artifact ID、version、hash 和 shot scope；“看起来都行”不能被无限外推到未来版本。

## 3. 建议审批门

| 门 | 用户看到什么 | 用户实际批准什么 | 批准后可进入 |
|---|---|---|---|
| G1 Shot Contract | 镜头表、总时长、可见动作、机位、连续性、广告功能、推断与 claim 边界 | Professional Shot Contract 的具体版本/hash | Canon 资产、Look、Storyboard Structure |
| G2 Canon Assets | 角色/产品/包装/材质/场景实际图与 QA | 每个独立 asset ID/version/hash 及授权角色 | Storyboard Final、Look final、K1 |
| G3 Global Look | Hero/State/Risk refs、Core/State/Delta 摘要 | Look Contract 与独立 refs | Storyboard Final、K1、P2 |
| G4 Storyboard Structure | N 格人审板、镜头顺序和节奏可读性 | N 个结构帧的 composition intent | Storyboard Final |
| G5 Storyboard Final | N 格最终人审板、逐帧身份/Look/continuity | 每个独立 final frame | V1、K1、P2 |
| G6 V1 | 无声整片 animatic、绝对时间线 | 节奏、切点、镜头边界和粗 blocking | K1、P1 |
| G7 K1 | 每镜 anchor 与状态账本 | 生成级静态状态和连续性 | P1、K2、V2 |
| G8 P1 | Generation Unit Map、provider 证据、预算、planned inputs | unit membership 与 capability profile | K2、V2 |
| G9 K2 | unit handoff records/anchors 或 single-unit exemption | 跨单元状态闭合 | V2、P2 |
| G10 V2 | 每 unit 无声 control video 与 motion tracks | 动态路径、blocking、cut、物理运动 | P2 |
| G11 P2 | master/unit/repair prompts、bindings、payload、diff/lock | 可提交的全能参考请求包 | 第三方平台提交 |

资产、Look 和 Storyboard Structure 可以在 Shot Contract 获批后并行准备，但任何下游消费都必须等待其所需上游各自获批并写入 Canon。

## 4. 用户看完生成视频后的返工不是 QC 工序

第三方平台生成后，由用户直接观看并描述问题。系统执行的是**反馈诊断与 owner routing**，不是另设一个独立 QC Skill。

诊断顺序：

1. 找到当次生成使用的冻结 P2 package、provider profile 和实际 attachment mapping。
2. 把用户观察映射到具体 Shot UID、Generation Unit、artifact 和 control role。
3. 比较实际请求是否已正确携带上游 Canon。
4. 选择唯一 Owner；不得把一个问题同时分配给多个 Owner“都改一点”。
5. 创建新 SemVer artifact；不原地修改已批准版本。
6. 标记精确 downstream descendants stale。
7. 运行 Owner validator、Canon transition 和所有受影响下游 validator。
8. 由用户重新批准修改面，再恢复到 P2。

## 5. Sole-owner 路由表

| 用户观察 | 唯一 Owner | 正确动作 | 不应做什么 |
|---|---|---|---|
| 故事、镜头数量/顺序、目标时长、广告功能错 | `ai-video-shot-script-director` | 改 Shot Contract，更新稳定 Shot UID 和依赖 | 用提示词偷偷改变镜头事实 |
| 用户改变已批准的规范性景别、机位角度或构图原则 | `ai-video-shot-script-director` | 新 Shot Contract 版本 | 只重画 Storyboard |
| 角色脸、体型、服装错 | 对应 character Owner | 修终端角色 Canon | 让 K1 猜新身份 |
| 产品几何、包装、标签 evidence、材质构造错 | 对应 product/packaging/material Owner | 修对应 Canon 资产 | 通过 Look 或 prompt 重塑产品 |
| 场景空间或固有环境错 | `scene-canon-asset-pack` | 修 Scene Canon | 用 storyboard 临时画面代替场景事实 |
| 全局色彩、光线、黑位、高光、颗粒、材质光学响应错 | `ai-video-global-look-lock` | 判断 Core/State/Delta 后最小修复 | 把整片问题拆成每镜 prompt patch |
| 已批准低机位，但某张代表静帧画成高机位 | `ai-video-modular-storyboard` | 只替换该 Shot UID 的独立帧 | 改 Shot Contract 的正确意图 |
| 静态 pose、产品朝向、液体状态或 continuity anchor 错 | `ai-video-keyframe-continuity-pack` | 修对应 K1/K2 anchor/ledger | 改 V2 运动掩盖静态状态错 |
| 起始构图正确，但运动中 camera path、speed、blocking、cut 或物理轨迹错 | `ai-video-timed-animatic-previs-director` | 修 V1 或 V2 | 改 Storyboard 静态帧 |
| alias 绑错、prompt 有歧义、unit split/reference budget/provider 序列化错 | `ai-video-omni-reference-prompt-director` | `revise` P1/P2 对应 owned surface | 修改上游 Canon |
| 请求包全部正确，但模型随机失败 | `ai-video-omni-reference-prompt-director` | 先原包重试，再最小强化约束、缩短 unit 或更换已验证 provider | 立即推翻所有上游资产 |

### 三类机位反馈必须分开

1. “我现在想把已批准的低机位改成高机位” → Shot Script Director。
2. “Shot Contract 要低机位，但 Storyboard 画成了高机位” → Modular Storyboard。
3. “开头是正确低机位，但运动过程镜头错误升高” → Previs Director。

## 6. 失效传播矩阵

| 上游变化 | 必须 stale | 通常可保留 |
|---|---|---|
| Shot count/order/duration | 受影响 Storyboard、V1、K1、P1、K2、V2、P2；若全局 timing 改则范围扩大 | 不依赖变更镜头的 Canon 资产 |
| Global Directing Grammar | 所有 storyboard/keyframe/unit/repair prompts；必要时 V1/V2 directing interpretation | 身份资产、Intrinsic Scene/Product Canon |
| Character/Product/Packaging/Material/Scene asset | 依赖它的 final storyboard、K1/K2、V2 appearance bindings、P2 | 无依赖镜头和其他资产 |
| Look Core | 所有 look-applied storyboard、keyframes、unit/repair prompts | 中性 V1/V2 timing/motion，除非可见性影响 blocking |
| Look State | 分配该 State 的镜头及下游 | 其他 States 的镜头 |
| Shot Look Delta | 指定 Shot UID 的 look-applied descendants | 所有其他镜头 |
| Storyboard frame | 对应 V1 blocking、K1、相关 P1/K2/V2/P2 | 其他独立 frame/hash |
| V1 timing | 受影响 K1 time anchors、P1、K2、V2、P2 | 静态 Canon、未受影响镜头 |
| K1 state | 受影响 K2、V2 bindings、P2 | V1 和无依赖 K1 anchors |
| P1 Generation Unit Plan | K2、所有相关 V2、bindings/prompts/payload | K1，只要 per-shot state 没变 |
| K2 | 对应 V2 与 P2 | K1、P1 |
| V2 | 对应 P2 unit/repair prompts | 上游静态资产和其他 units |
| Provider capability | provider payload、capacity report；可能触发 P1 unit replan | 若语义没变，Canonical IR 可保留 |
| Prompt-owned wording/alias | 对应 prompt/binding/payload | 所有上游事实 |

## 7. 局部故事板修改事务

修改一格或多格时：

1. 用稳定 `shot_uid` 指定目标，不使用显示位置作为身份。
2. 在新版本中 staging 替换文件，旧批准帧保持 active。
3. 每个新图在下一回合进行真实视觉检查、尺寸与 hash 记录。
4. 只有全部请求帧都通过才原子 commit；任意一帧失败则整笔 transaction 拒绝，旧 manifest 不变。
5. 未受影响帧保持 byte-identical。
6. 重新确定性合成 review board。
7. 只失效依赖修改帧的 K1/V1/V2/P2。

如果用户要求增删、合并、拆分或重排镜头，Storyboard Owner 只能输出 `routed_upstream` transaction，实际修改由 Shot Script Director 完成。

## 8. Prompt Director revise 的证据门

P2 的 prompt-owned revise 必须读取：

- previous Canonical IR 文件及 file hash；
- previous dependency lockfile 及 file hash；
- previous package ID/version/hash；
- 本次用户反馈与 affected Shot UIDs/units；
- 当前完整 Canon 和 provider evidence。

输出必须提供：

- 新版本 package；
- 机器可读 before/after diff；
- changed paths 与 unchanged paths 的完整、互斥分区；
- 每个 unchanged output 的原始 byte hash；
- 新 binding/prompt/payload/lockfile；
- 若非 Prompt Owner，则输出 exact `upstream_change_request`，不生成矛盾 patch。

## 9. Canon transaction 恢复

任何现有 Canon mutation 都必须保存：

```text
BASE_PROJECT_CANON_SNAPSHOT.json
CANDIDATE_PROJECT_CANON_POST.json
base raw file SHA-256
owner delta
MANIFEST_UPDATE_RECEIPT.json（只在实际 post readback 后）
```

若运行中断：

- Canon 已替换但 receipt 缺失：只有 immutable base/delta/owner record 与当前 post manifest 能证明同一合法 transaction 时，才能重建 receipt。
- 只准备了 base/delta，尚未替换 Canon：同一 Owner 可在字节完全一致时恢复 compare-and-swap；任何差异 fail closed。
- 存在 `PENDING_PROJECT_CANON_TRANSACTION.json`：其他 Owner 不得越过，必须先恢复或明确阻塞。
- 不得手工写一个“applied” receipt 来掩盖未完成状态。

## 10. 真正的硬阻塞报告

只有唯一且不可替代的外部条件缺失时才报告硬阻塞。报告必须包含：

```text
缺少什么：精确文件、证据、权限、provider modality 或 legally material fact
为什么无法绕过：说明任何替代为什么会改变作品身份、真实性或合法 generation route
已经完成什么：列出不受影响且已验证的 artifact/version/hash
解除后怎么继续：唯一恢复阶段、Owner、validator 与需要重建的 descendants
```

困难、耗时、希望用户补专业导演语言、模型可能随机失败、或某阶段尚未做完，都不构成硬阻塞。
