# 宿主、实际派发与入口

正式生产使用显式 `$visual-exploration-moodboard` 并完整加载 SKILL.md 和当前必要资源。自动发现保持开启；它不代替实际读取/注入和执行证据。`agents/openai.yaml` 仅UI元数据/调用策略，不是专业角色配置，也不切换正在运行的模型。

## 实际可用入口

从本包根目录运行 `node scripts/moodboard.mjs --help`，再查看所需子命令帮助；只使用当前实现接受的参数。探测、准备或manifest写入成功不等于代理已启动；命令、正常结果、失败状态和实际回执须同时对应。包在开发/升级中时保持不支持项准确，不根据SPEC候选命令编造成功。

当前精确入口如下；依赖和Chromium探测使用 `probe`，真实GPU由 `render` 验证。

```powershell
npm ci
node scripts/moodboard.mjs probe
node scripts/moodboard.mjs start --project "工程目录" --brief "原始brief.md" --host native
node scripts/moodboard.mjs start --project "另一个新工程目录" --brief "原始brief.md" --host codex-app-server --codex "实际codex.exe的绝对路径"
node scripts/moodboard.mjs resume --project "工程目录" --host native --codex "实际codex.exe的绝对路径" --trace "已授权实际运行日志.jsonl"
```

`start` 保留原始MD/TXT或项目JSON和intake。原生无trace只到prepared，随后由当前主责/原生代理实际工作，按同一工程resume导入授权日志；外部适配器实际执行ephemeral turn。尚无project.json时，真实主责先理解原brief并编写项目JSON，调用 `init --project "工程目录" --brief "代理编写项目.json"`；init只创建合同，不代表已启动。子代理只调用init/commit/render/export/check，不递归调用start。resume保护已有项目。

原生导入需当前SKILL全文的实际成功读取回执，及其后同一SolUltra turn内与本工程相关的成功工具动作。只接受一个有ID的session；call和output须同session/turn，跨界或矛盾保持unverified。命令回执须有真实支持schema的正面完成依据（如exit_code=0及output字符串）；空/null、未知文字、运行中及结构化失败都不能通过。代码模式包装须保留成功子工具结果，只有“Script completed”或被裁掉退出状态的输出不足够。命令的实际cwd、受支持CLI路径参数或API字面量参数按规范化完整路径关联，明确指向其他工程不能靠本工程cwd或同名前缀补救；注释/echo中的路径不算绑定。动态或未支持的调用语法准确保留未验证，不猜测执行意义。

传实际codex可执行程序以核版本/hash；无法核实程序或当前内容则unverified。导入为显式指定的授权日志，不扫描其他聊天；原始快照只保存在工程证据中，不进入公共包。它证明本地可观察记录，不提供模型理解或提供方密码学认证。交付门调用validateHostEvidence重新解析精确rawTrace，并核当前适配器/Skill/程序、session/turn及派生动作与回执逐项一致；app-server同样重派生握手、刷新目录、服务解析的SolUltra、显式Skill turn、成功完成和工程工具结果。普通占位、非JSONL、摘要矛盾、旧适配器或缺实际完成均不能靠手填executed通过；这种本地一致性检查不声称识别全套伪造的提供方事实。

两种宿主执行形态使用同一项目合同：

- 当前原生宿主：主责加载Skill，调用包内准备/校验，然后用当前宿主真正支持的原生代理/工具执行；保留实际派发、载入与回传。只准备了任务包而尚未派发，状态是pending。
- 外部Codex app-server适配：只有对实际程序/schema/协议探测并实派验证后才能用；显式Skill输入、SolUltra、模型动作和工具结果需真实回执。unsupported或未知结果不假装降级成已执行；未知派发结果先查原任务，避免盲重发。

适配器握手请求最多30秒，完整任务默认15分钟；start/resume可按已有预算传 `--timeout-ms`（1000至3600000毫秒），直接API调用可传timeoutMs。运行中持续写工程内原始JSONL；超时请求中断并保留unverified和已发生证据，不盲重发。正常完成只在服务端解析SolUltra配置、显式Skill turn完成和成功工具结果齐备时记executed；服务端运行配置与完成事件是宿主等价证据，不冒称捕获了turn_context或模型理解。当前0.160已实跑该链路；其他程序须自己探测，旧入口握手/发现成功不自动获得完整任务支持。[官方 App Server 文档](https://developers.openai.com/codex/app-server/)

CLI工具并不天然具有Codex图像或派发能力。需要媒体工具时由真实宿主调用；只有提示文本供用户转发不满足代理执行合同。角色上下文使用包内 [主责](../prompts/creative-director.md)、[技术执行](../prompts/creative-technologist.md)、[独立审阅](../prompts/independent-reviewer.md)，实际派发时附本次材料，不把模板文件存在当真实代理启动。

## 可检查的证据

记录实际宿主程序绝对路径、版本、文件哈希、能力探测、Skill路径/版本/哈希、实际可见输入/读取与工具轨迹，以及运行ID/模型/档位。桌面和PATH可能是不同程序；不能用PATH版本替代桌面入口。先验证一个实际入口，再核第二入口；未知入口准确限定支持范围，不迁移全局配置或建设新常驻agent server。

所有Codex语言代理使用 `gpt-6.1-sol` / `ultra`。支持创建/接续参数时显式指定，使用对应工具允许的历史继承方式；完整历史继承须先核父代理实际一致。核对实际 `turn_context` 或等价记录，默认配置/提示文字/实际运行分别取证，不声称修改了旧回合。不支持选择/核对时说明具体限制，不擅自换模型。

工具可核实文本被交付与版本关系，不能证明模型理解。新代理前向使用必须执行真实任务、查看结果并局部修订；不得只填skill_loaded/verified或假type=skill记录。缺使用、绘制、同版检查或审阅时，交付状态不能ready；若实际工具不能强制某项，写明未验证而非假保护。

本包核心不得依赖固定D盘路径、兄弟Skill、仓库路由器或隐藏聊天。公共源码维护可按所在仓库现有授权同步，业务作品发布、上传素材、账户/费用动作须按当次权限处理；正常本地制作修复不增加无依据审批。
