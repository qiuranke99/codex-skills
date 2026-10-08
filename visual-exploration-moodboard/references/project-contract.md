# 项目、来源与快照合同

工程在用户目录，Skill 包仅保存通用实现、自编合法配方与通用测试。原项目已有运行/素材索引时引用或扩展，不建立跨项目资产权威。

## 可编辑项目

`project.json` 的 `schemaVersion` 为 `1`。下列是当前集成数据关系，精确可接受字段/类型以包内验证入口为准，不把文档字段存在当品质证明。

| 位置 | 内容 |
| --- | --- |
| project | id、title、subtitle、medium、createdAt |
| brief | decision；objectSuccess/carrierSuccess 字符串数组；locks 数组；openVariables 字符串数组 |
| locks 项 | 可包含 assetId/property/allowedOperations/regionRef/sourceRef，引用当前授权和不可变属性 |
| benchmarks | revision；object/carrier 数组；每项含 id/url/reason/observe/criticalGap/observed；真实观察另有可定位证据，observed:true 不充分 |
| directions 项 | id/title/subtitle/description/claim；hypothesis 的 question/mechanism/expected/failure；handoff 的 adopt/exclude/unproven；recipeId、完整 parameters、snapshot、poster |
| quality | object/carrier 各自 status/evidence/ issues；声明状态不自动授予通过 |
| 可选方向素材 | assets 的 url/role/caption/sourceRef、rights/authorization/operation；最小可执行结构见 asset-operations.md。palette 可选 |
| 主体与光场同场研究 | studyComposition 的 baseAssetId/maskAssetId/opacity/blendMode/aspectRatio/purpose；只引用本方向唯一、可嵌入且 presentation 为 composition-only 的资产；实际操作及 maskRef 必须吻合授权。compositionPoster 是实际浏览器合成采集，poster 仍是纯Shader GPU证据，两者不可替换 |

原始 brief 与最新真人反馈保留原文来源。专业观察、来源/授权、参考拆解、执行、检查、审阅可采用项目内 sidecar，并以 `{path, sha256, kind, scope}` 关联：路径须实际存在且在允许目录内，哈希和覆盖范围须匹配当前产物。缺文件、空正文、错版本或自由填写 verified 字段不算证据。

来源分清用户/项目事实原件、真实外部参考、AI 概念、Shaders 与混合派生。资产 ID 管关系，字节哈希管内容；记录原位置、许可、角色、实际观察、使用范围、编辑授权、区域/掩模版本、不可变属性及父资产/转换链。身份资产或外部参考不因可访问便可再分发。批准记录区分网页点击、主责推荐、真人明确许可及下游批准。

## 版本关系

在包目录使用以下已实现入口；参数文件是完整合法JSON，暂停选帧的时间单位是秒。

```powershell
node scripts/moodboard.mjs commit --project "工程目录" --direction "方向ID" --time 2.5 --parameters "完整参数.json"
node scripts/moodboard.mjs render --project "工程目录"
node scripts/moodboard.mjs serve --project "工程目录" --port 0
node scripts/moodboard.mjs export --project "工程目录" --format png
node scripts/moodboard.mjs export --project "工程目录" --format pdf
node scripts/moodboard.mjs check --project "工程目录" --scope technical
node scripts/moodboard.mjs check --project "工程目录" --scope delivery
```

`serve` 返回回环URL，Ctrl+C关闭；`render`处理当前项目方向，不接受SPEC早期候选的--direction参数。PNG/PDF导出范围为当前完整总览；未支持视频准确拒绝。最终证据门使用delivery检查，没有单独finalize命令。检查退出0仅证明声明的证据关系，自评及审美结论仍按品质合同判断。

本地服务绑定启动构建；运行源或依赖改变后拒绝继续API操作并要求重启，不能把旧JS bundle配新回执。网页重开会取得逐方向快照校验状态，失效显示明确原因。导出通过同源POST `/api/export`、JSON `{ "format": "png" }` 或 `pdf` 发起；GET不启动生成。PNG/PDF均包含每个方向自己的主体素材、Shader选帧、假设与交接，PDF按方向分页。

快照由服务校验/提交，不从网页临时参数直接宣布同版：包含 id/digest/timeSeconds/parameters/recipeDigest/revision，并关联当前配方/适配器、锁定依赖、有效默认值、源资产与渲染设置。对于支持的程序研究保存可重建时间/初态/步序；未支持的状态模拟/随机/视频时钟不能伪称确定性。

浏览器显示 dirty 状态；保存、导出、审阅当前状态须先提交。HTML、poster、导出、绘制回执、技术/观看检查和审阅均指向准确快照与构建。显式导出旧版时显示旧版，不混当前参数和旧 poster。依赖、源资产、配方或构建变化使受影响证据失效；未变化方向可沿用准确版本。缺源文件或状态不可重建时返回具体不足，不静默用默认值恢复通过。

## 交接与状态

交付包括可运行 HTML/本地资源与编辑源、同版 PNG、项目所需 PDF、三类交接、许可、实际入口/支持范围、当前检查/独立审阅、未解决项及重开方法。首版产品的 PDF 能力必须真实验证，单项目无需默认生成。未支持动态格式准确拒绝，不把拒绝算支持通过。

至少区分技术、对象品质、承载品质、独立审阅、交付、用户接受。ready 要求完整方向真实 Shader 相关作用、当前版本产物/证据、两类竞争力依据及对应独立审阅；机械检查只验证关系，不能颁发审美认证。缺项保留 partial/unverified/needs_revision/unsupported，独立条件不足保留 independent_review_pending。

`createProject`保存hash绑定的`baselineRef`，其中保存真实initialProject/initialProjectDigest/projectIdentityDigest、初始brief/benchmarks。delivery核验实际内容、所属项目及早于制作的时间关系；当前brief或benchmarks改变，需在baselineChanges中引用结构化baseline-change，绑定前后摘要、原baseline哈希、真实changedAt、reason及affectedScope，不能换成其他项目或任意更早文件。历史格式升级保留originalBaselineRef，准确记录upgradedAt，不覆盖原件。

正式render/export固定1440×1000视口、DPR1、light/reduce、SDR sRGB采集规格，进入快照renderProfile；响应式浏览是独立预览，不得用手机尺寸覆盖同快照权威海报。capture显式传不同设置会拒绝；浏览器回执记录实际canvas色彩/色调映射及环境。输出PNG实际解码并与GPU读回像素、尺寸绑定。PNG/PDF回执和独立审阅的renderBindings另绑定每方向snapshot/engine/profile/实际output路径与字节哈希/decodedDigest/尺寸；重复采集同像素不因回执时间变化无故失效，真实输出变化使旧导出/审阅失效。

声明式studyComposition用于让对象与同一真实Shader直接共同观看，base/mask须真实decode，实际CSS混合、作用范围与合同一致。主板可关闭光场作同条件对照，关闭时保留partial并禁止完整导出；正式采集恢复并校验enabled。合成定义进snapshot.compositionDigest；render.composition与renderBindings.composition绑定实际主体画面、掩模定义及解码像素。compare/PNG/PDF优先展示compositionPoster，纯光场只作拆解。掩模成立不证明身份/材质或物理正确，仍需专业查看最终影响。

素材/假设/可见caption变化、当前依赖代码变化都使快照失效；同摘要幂等提交亦验证磁盘快照。宿主证据重新派生原始JSONL，不能只填executed。

独立艺术回执为`schemaVersion:1, kind:"independent-art-review"`，保留现有reviewer/participatedInProduction/engineDigest/benchmarkRevision/directions/initialReview/independentOrderEvidence。顺序文件是`schemaVersion:1, kind:"independent-review-order"`，含同一reviewer、participatedInProduction:false、executionConclusionsSeenBeforeInitialReview:false、acknowledgedAt/initialSealedAt、可选comparisonOpenedAt，以及ackRef/runtimeRef/initialReview的实际hash引用。该结构核对记录及版本，不能证明阅读心理顺序或代理判断的审美真实性。首评不支持的方向仍不能交付ready。
