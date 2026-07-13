# 工具、Skill、输入与输出

## 1. 系统组成

High-Control suite 包含 15 个 Skill，其中 13 个构成生产核心，2 个只用于
前期探索；同一 GitHub release 还发布 1 个 manifest 声明的独立复杂产品
production Skill。

所有 16 个 publication Skill 的共同前置输入是 GitHub-latest release attestation。
OS-native `release-control.ps1` / `release-control.sh` 固定运行时入口执行
`check --project-root <PROJECT_ROOT>` 后必须返回
`ready_latest=true`，并生成/更新 `00_project_canon/SYSTEM_RUNTIME_LOCK.json`；
该锁绑定 repository id、`main` commit、Git tree、manifest/runtime hashes、
16 个 Skill tree、release receipt、操作系统级只读 snapshot 证据和新 Codex
task。生产门必须证明 snapshot 拒绝创建文件与获取写句柄；任何旧、离线、
可写、漂移或混代状态都不得进入下列 Owner 合同。

### 六个新增流程 Owner

| Skill | 唯一责任 | 主要输入 | 主要输出 | 不负责 |
|---|---|---|---|---|
| `ai-video-shot-script-director` | 把粗脚本升级为唯一专业镜头事实源 | idea、shot table、DOCX/TXT/MD、用户事实 | Professional Shot Contract、Global Directing、asset/keyframe/previs maps、Project Canon | 图像、视频提示词、provider payload |
| `ai-video-global-look-lock` | 全片视觉语言与合法变化 | Shot Contract、Canon 资产、可选 look refs | Look Core、Look States、Shot Deltas、独立 Look Reference Set | 身份、构图、运动、调色后期 |
| `ai-video-modular-storyboard` | 一镜一文件的可编辑故事板 | Shot Contract、Canon 资产、Global Look | N 个独立结构/最终帧、确定性人审板、局部事务 | 镜头数量/顺序、关键帧、Previs |
| `ai-video-timed-animatic-previs-director` | 时间、镜头边界、动态路径和物理运动 | Shot Contract、Storyboard、V1/K1/P1/K2 | V1、V2、timing/camera/blocking/physics maps | 身份、Look、模型选择、成片剪辑 |
| `ai-video-keyframe-continuity-pack` | 生成级静态锚点与状态连续性 | K1：Canon 资产、Storyboard Final、Global Look、V1；K2：冻结 K1、approved P1 | K1、状态账本、K2 边界补充 | 首尾帧模式、视频提示词、运动路径 |
| `ai-video-omni-reference-prompt-director` | Generation Unit、参考绑定、提示词和 provider 序列化 | 完整 Canon、K1/P1/K2/V2、能力证据 | P1、P2、IR、binding、prompts、payload、lockfile | 创作上游事实、实际调用视频 API、QC |

### 七个 Canon 资产 Owner

| Skill | 使用条件 | Canon 注意事项 |
|---|---|---|
| `character-casting-lock-board` | 角色初选：大正脸 + 前/后/侧完整全身 | 默认是 pre-Canon selection；只有显式 `casting_as_terminal` 才能成为终端角色 Authority |
| `character-final-lock-board` | 需要身份、服装、多角度、表情和细节的终端角色 | 与 single-face 路线二选一；同一 `asset_key` 不能双终端 |
| `single-face-character-lock-board` | 整板只能出现一个可见人脸，同时要无头前/后服装视图 | 与 final-character 路线二选一 |
| `multi-angle-product-identity-lock-board` | 普通、低风险、主要不透明产品 | 不适用于标签文字优先、玻璃/液体/反光或复杂机械状态 |
| `packaging-product-identity-label-lock-board` | 瓶、盒、袋、罐、管、罐头等标签/包装结构 | exact copy 只有来源和确定性 OCR/解码证据才能批准 |
| `material-sensitive-product-master-asset-board` | 玻璃、透明、液体、乳霜、反光、镜面、磨砂、多层产品 | 锁定材质行为和结构证据，不猜隐藏机制 |
| `scene-canon-asset-pack` | 需要复用的场景、环境、空间和 unseen-space 扩展 | 分离场景固有事实与临时光线/镜头/后期效果 |

### 两个可选探索 Skill

| Skill | 何时使用 | 是否进入 Canon |
|---|---|---|
| `cinematic_shot_image_explorer` | 在正式 Shot Contract 前探索 10 个电影镜头方向 | 默认不进入；只有经正确 Owner 转化、检查和批准后才可成为证据 |
| `cinematic_world_builder` | 前期探索人物、建筑、环境、文化等 9 个世界视觉方向 | 默认不进入；不能替代 Scene Canon 或 Global Look |

探索 Skill 不在 0–11 主链中，不能用来绕过任何 Canon Owner。

## 2. 外部工具与运行依赖

| 工具/能力 | 用途 | 必需阶段 | 最低验收 |
|---|---|---|---|
| Codex Desktop / Codex CLI | 读取 Skill、编制 artifact、运行 validator、协调图像生成与返工 | 全程 | 能发现本仓库 Skill；能读写项目目录；重启后 `$skill-name` 可触发 |
| Codex Image Generation | 生成资产板、Look refs、Storyboard、K1/K2 | 2、3、4A/4B、6、8（按需） | 每次生成前提示词 sidecar 已冻结；生成调用为回合最后动作；下一回合实际检查 |
| 固定 Python 3.11/3.12 runtime | 运行 schema、hash、Canon transition 和 package validator | 全程 | OS-native launcher 能解析已验证解释器；禁止用未验证的全局 Python 替代 |
| Pillow `11.3.0` | 图片解码、review board、Canon 资产验证、deterministic atlas | 2、4A/4B、6、7、8、10 | 版本与两个 requirements pin 一致；真实 decode/verify/load 通过 |
| FFmpeg + ffprobe | V1/V2 构建与实时媒体验证；P1/P2 检查视频/音频 | 5、7、9、10 | 位于 PATH；可解析 codec、duration、streams、fps、尺寸、帧/packet 数和 chapters |
| 文档转换器 | 提取旧 `.doc`/`.rtf` | 0（仅旧格式） | macOS 可使用 `textutil`；Windows 使用 Word/受信任转换器；输出和转换器身份可记录并 hash |
| 中性 Previs 工具 | 制作 V1；为复杂单元制作 V2 camera/blocking/physics control video | 5、9 | 可输出符合阶段/provider 约束的无声视频；视觉中性；不声称拥有身份或最终 Look |
| 第三方视频平台/API | P2 之后实际生成视频 | 本 SOP 之外 | 必须暴露经验证的 Omni multimodal surface；凭据和提交动作由用户/外部系统管理 |

Previs 工具不绑定品牌。可以使用确定性 2D animatic、中性 3D blocking、Prevzi 导演台、Blender 或其他能满足 V2 合同的工具。关键不是软件名称，而是时间边界、运动轨迹、媒体规格和证据可验证。

## 3. 跨平台运行检查

### Windows

- Skill 根目录应由当前 Codex 能发现；只保留一份同名 Skill，避免 `.agents/skills` 与 `.codex/skills` 双挂载。
- Python、Pillow、FFmpeg 和 ffprobe 必须能从启动 Codex 的同一环境访问。
- 路径使用绝对 Windows 路径；命令层为含空格路径加引号。
- 旧 `.doc`/`.rtf` 先另存为 `.docx`，或使用可记录身份与输出 hash 的确定性转换器。
- 若公司策略禁止本地脚本、图像生成或读写项目目录，先解决策略权限；安装 Skill 本身不能绕过它。

### macOS

- 可使用 `python3`；确保 Pillow 安装在 Codex 实际调用的同一解释器环境。
- FFmpeg/ffprobe 位于 PATH。
- 旧 Word 文档可由 `textutil` 提取，但仍需保存源字节 hash 和 extraction report。
- 路径包含空格时使用完整绝对路径并正确引用。

### 一次性 Preflight

在真实项目开始前，Codex 应验证：

```text
[ ] 16 个 publication Skill 全部来自同一 release；其中 13 个 suite 核心 Skill 可发现
[ ] Python 可运行
[ ] Pillow 精确版本可导入
[ ] ffmpeg 和 ffprobe 可运行
[ ] 项目目录可读写
[ ] 源脚本可确定性提取
[ ] Image Generation 可用
[ ] Provider capability evidence 已获得，或明确记录为 P1 前 blocker
[ ] 不存在未恢复的 PENDING_PROJECT_CANON_TRANSACTION
```

## 4. 最小项目输入

系统可以从以下最低输入开始：

- 一个粗创意、镜头表、DOCX/TXT/MD 或用户消息；
- 明确要制作广告的产品/服务身份；
- 用户实际拥有的参考文件；
- 可选目标时长和比例。

以下都不是启动 blocker：

- 没有专业镜头语言；
- 没有写出完整产品使用逻辑；
- 没有 lens、camera height、blocking 或 transition；
- 没有现成 Look reference；
- 暂时没有 provider profile（它只在 P1 前成为硬门）。

以下可能成为局部或真实 blocker：

- 源文件不可读取且无法确定性转换；
- 两个相互排斥的品牌方向会改变作品身份；
- 必须出现的 legally material claim/copy 没有来源；
- 目标产品的复杂机械结构没有任何证据或适用 Canon Owner；
- Provider 不支持某个生成单元必需的 multimodal modality；
- 当前平台只提供 T2V、classic I2V 或 endpoint-frame surface。

## 5. 0–11 节点输入/输出合同

| 阶段 | 必需输入 | 可选输入 | 机器事实输出 | 人类审阅输出 |
|---|---|---|---|---|
| 0 Intake | 原始粗脚本/创意文件 | brief、参考索引 | Source Evidence、Extraction Report、源文件 hashes | 输入清单与不可读字段说明 |
| 1 Shot Contract | 节点 0 证据 | duration、ratio、campaign、copy、claims | Shot Contract JSON、Canon、source hashes、inference/claim ledger | 专业分镜可读版、镜头时长表 |
| 2 Canon Assets | Shot asset map、源参考 | 衣服、鞋、道具、补充角度 | Owner artifact records、binary hashes、Canon entries | 角色/产品/包装/材质/场景资产板 |
| 3 Global Look | Shot Contract、Canon 资产 | look images、treatment、color cards | Look Contract、Core/State/Delta、reference records | Hero/State/Risk look refs、Look 摘要 |
| 4A Storyboard Structure | Shot Contract、authoritative required Canon refs | provisional look | 独立 structure-frame records、transaction | N 格确定性人审板 |
| 4B Storyboard Final | Approved structure、final Canon/Look | 无 | 独立 final-frame records、prompt sidecars、hashes | 最终 N 格确定性人审板 |
| 5 V1 | Shot Contract、Storyboard Final | neutral proxies | Previs manifest、V1 MP4、timing map、probe evidence | 整片无声 timing animatic |
| 6 K1 | Shot/Canon/Look/Storyboard/V1 | single-static exemption | K1 manifest、state ledgers、anchors、prompt sidecars | 每镜关键帧与连续性说明 |
| 7 P1 | 完整 Canon snapshot、provider evidence | atlas candidates | Generation Unit Plan、model/provider profiles、dry-build receipts | 单元/预算/阻塞摘要 |
| 8 K2 | Frozen K1、approved P1 | 无 | Boundary Supplement 或 exemption、boundary anchors | 跨单元 handoff 摘要 |
| 9 V2 | V1/K1/P1/K2、runtime evidence | 外部中性 Previs files | V2 MP4、trajectory/blocking/physics tracks、probe evidence | 每 unit control previs |
| 10 P2 | compile Canon snapshot、P1/K2/V2、全部批准资产 | source-approved dialogue/SFX | Canonical IR、bindings、2.5/2.0 renders、unit/repair prompts、payload、lockfile | Prompt/package 摘要与反馈路由 |
| 11 User Review | 第三方候选视频、冻结 P2 请求包 | 用户观察 | 接受记录，或唯一 Owner change request 与 stale 范围 | 用户接受结果或精确返工说明 |

## 6. Provider evidence 的证据等级

能力信息按以下顺序使用：

1. 当前 provider 实际 schema/API/UI surface 的可保存证据；
2. 官方 first-party model documentation；
3. provider 帮助中心或平台文档；
4. preview、发布演示、用户转述或社区经验。

第 4 级只能记录为 `runtime_verified:false`，不能控制 duration/reference budget。模型名相同不等于第三方平台暴露相同 surface。

每个 provider snapshot 至少锁定：

```text
profile identity
provider + surface/endpoint + model ID + backend binding
generation mode
supported input modalities
per-modality and total counts
video/image/audio input constraints
duration/bytes/dimensions/aspect/fps
MIME/container/codec/audio-track policy
evidence source + captured_at + file SHA-256
unknown or unverified fields
```

P1 规划时使用模型 baseline 与 provider snapshot 的**更严格交集**。V2/P2 必须再次对真实媒体文件做 live inspection，不能只相信先前存下来的 probe metadata。

## 7. Project Canon 与 artifact 的区别

Project Canon 是索引，不是内容本身。生产 artifact 依赖其他具体 artifact 的 ID/version/hash，不依赖 Canon 文件的 hash；否则每次登记一个新资产都会形成全图 hash 循环。

每个非 draft artifact 使用共享 envelope：

```yaml
contract_version: ai-video-artifact-v1
artifact_id:
owner_skill:
version:
sha256:
approval_status:
dependencies:
affected_shot_uids:
stale_reason:
```

二进制文件还要单独记录 `file_sha256`。Canon 同时锁定二进制 locator/hash 和 producer-owned artifact-record locator/hash。receipt 只说明一次写入的结果，必须同时验证 immutable base snapshot、actual post Canon 和真实文件。

## 8. P2 提交给第三方平台时的输入角色

P2 会把每个选择的参考绑定到一个或多个控制角色，例如：

- identity、wardrobe；
- product geometry、label evidence、material behavior；
- scene canon；
- global look；
- storyboard composition；
- keyframe state、keyframe boundary；
- camera path、blocking、physical motion、Control Previs；
- source-approved dialogue voice 或 synchronous SFX（若用户提供且 provider 支持）。

一个文件承担多个角色时只计算一次 attachment，但必须保留完整角色集。音乐/配乐不属于本系统的绑定角色。

如果参考数超限，严格按以下顺序处理：

1. 在 continuity-safe Shot UID 边界拆分 generation unit；
2. 删除真正 irrelevant 或 superseded 的证据；
3. 若 provider 按图片数量计数且微小文字不是该图职责，构建无缩放、确定性、可追溯的 unit-specific atlas；
4. 仍无法容纳则阻塞，不得静默丢失 required control。
