# 项目目录与跨设备工作方式

本文件的目录模板可供独立 Skill 共同写入一个 Project Canon；其中的
`SYSTEM_RUNTIME_LOCK.json`、同 revision snapshot 与阶段 release check 只在
用户显式选择 aggregate-managed workflow 时启用。它们不决定单包是否安装、
可发现、可调用或验证通过。

## 1. Skill 发现位置与项目根不能混淆

### 独立 Skill 发现

每个顶层 Skill 都可以单独复制或链接到任一受支持的 Codex discovery root。
该包自己的 `SKILL.md` 和 package-local validator 是其运行权威。独立 Skill
不要求 `high-control-ai-tvc`、suite receipt、兄弟目录或同一个 release。

### 可选 aggregate snapshot 根

当用户明确选择 aggregate profile 时，`release_control.py sync` 从 GitHub
`main` 精确 OID 建立并验证一个不可变 snapshot，批量工具从中暴露所选
entries。下面的兄弟目录树只是该 aggregate snapshot 的内部布局，用于兼容性
readback；它不是单包安装或调用条件。

```text
<SKILL_ROOT>/
├── ai-video-shot-script-director/
├── ai-video-global-look-lock/
├── ai-video-modular-storyboard/
├── ai-video-timed-animatic-previs-director/
├── ai-video-keyframe-continuity-pack/
├── ai-video-omni-reference-prompt-director/
├── character-casting-lock-board/
├── character-final-lock-board/
├── single-face-character-lock-board/
├── multi-angle-product-identity-lock-board/
├── packaging-product-identity-label-lock-board/
├── material-sensitive-product-master-asset-board/
├── scene-canon-asset-pack/
├── cinematic_shot_image_explorer/          # optional
├── cinematic_world_builder/                 # optional
├── advertising-reference-research-director/ # excluded from aggregate only; still standalone
├── complex-product-identity-reconstruction-asset-locking/ # excluded from aggregate only; still standalone
└── frozen-moment-camera-coverage/            # excluded from aggregate only; still standalone
```

不要把同名 Skill 同时暴露到多个 Codex discovery root。独立任务只安装实际
需要的包即可；只有 opt-in aggregate workflow 才校验所选 Owner 集合和
snapshot 内的同 revision 布局。

### Production Project Root

这是某一支广告的源文件、Canon 和生产 artifact 所在位置。它不应放进 Skill 安装目录。

Windows 建议：

```text
C:\AI-TVC\<project_id>
```

macOS 建议：

```text
/Volumes/<work-disk>/AI-TVC/<project_id>
```

## 2. 推荐 Production Project 模板

目录按阶段实际创建；不要提前生成空白假 artifact。

```text
<PROJECT_ROOT>/
├── 00_project_canon/
│   ├── PROJECT_CANON_MANIFEST.json
│   ├── SYSTEM_RUNTIME_LOCK.json                  # 仅 aggregate-managed：当前阶段 snapshot/receipt/runtime/task
│   ├── PENDING_PROJECT_CANON_TRANSACTION.json       # 仅 transaction 未收口时存在
│   └── .canon.lock                                  # runtime lock
│
├── 01_sources/
│   ├── script/
│   │   ├── original/                                # 原始字节，禁止覆盖
│   │   └── extracted/                               # 确定性提取文本与报告
│   ├── character/
│   ├── product/
│   ├── packaging/
│   ├── scene/
│   ├── look/
│   └── provider/
│
├── 02_shot_contract/
│   └── <package_id>/
│       ├── 00_manifest/
│       ├── PROFESSIONAL_SHOT_CONTRACT.json
│       └── PROFESSIONAL_SHOT_CONTRACT.md
│
├── 03_canon_assets/
│   ├── character/<asset_key>/<package_id>/
│   ├── product/<asset_key>/<package_id>/
│   ├── packaging/<asset_key>/<package_id>/
│   ├── material/<asset_key>/<package_id>/
│   └── scene/<asset_key>/<package_id>/
│
├── 04_global_look/
│   └── <package_id>/
│       ├── 00_manifest/
│       ├── references/
│       └── reports/
│
├── 05_storyboard/
│   └── <package_id>/
│       ├── 00_manifest/
│       ├── 01_frames/<shot_uid>/
│       ├── 02_review_board/
│       ├── 03_transactions/
│       └── 04_qa/
│
├── 06_previs/
│   └── <package_id>/
│       ├── 00_manifest/
│       ├── 01_timing_animatic_v1/
│       ├── 02_control_previs_v2/<generation_unit_id>/
│       ├── 03_motion/
│       └── 04_qa/
│
├── outputs/
│   ├── ai-video-keyframes/<project_id>/<package_id>/
│   │   ├── 00_manifest/
│   │   ├── 01_keyframes/<shot_uid>/
│   │   ├── 02_ledgers/
│   │   ├── 03_boundaries/
│   │   └── 04_reports/
│   └── ai-video-prompts/<project_id>/<package_id>/
│       ├── 00_manifest/
│       ├── 01_bindings/
│       ├── 02_prompts/
│       ├── 03_payload/
│       ├── 04_reports/
│       └── owned_artifacts/
│
├── 10_user_review/
│   ├── provider_runs/                               # 可选：只存用户主动带回的 run 证据
│   └── feedback/                                    # 用户观察与 route records
│
└── 99_archive/
    └── exported_readonly_snapshots/                 # 可选，不能冒充当前 Canon
```

对显式 aggregate-managed 项目，每个阶段入口由 OS-native
`release-control.ps1` / `release-control.sh` 的
`check --project-root <PROJECT_ROOT>` 原子更新 `SYSTEM_RUNTIME_LOCK.json`。
存在 pending Canon transaction 时不得迁移 aggregate snapshot；GitHub
`main` 前进后先 `sync`、启动新 Codex task，再写入新锁。独立 Skill 不读取
这个锁来判断自身 availability。

各 Skill 的实际 schema 与 package tree 优先于这个便于人类理解的总览。不要为了匹配示意图而重命名 Skill 合同要求的文件。

## 3. 命名规则

### Project ID

使用稳定、跨平台、无空格的短名：

```text
bath-oil-tvc-2026
brand-product-campaign-a
```

### Shot UID

使用稳定身份，不把显示位置当身份：

```text
S001, S002, S003 ...
```

- 显示镜号可以变化；Shot UID 不随排版变化。
- 增删、拆分、合并镜头由 Shot Script Director 创建新稳定 UID。
- Storyboard、V1、K1、P1、K2、V2、P2 都以 Shot UID 关联。

### Generation Unit ID

只由 P1 创建：

```text
GU001, GU002 ...
```

K1 不得提前写 Generation Unit ID。Unit 只包含连续、完整、按顺序的 Shot UIDs。

### Artifact 与 Package

- 每个 Owner 使用稳定 `artifact_id` 和递增 SemVer。
- 已批准 artifact 不原地覆盖；新版本写新 artifact/hash。
- 二进制文件保留原生扩展名，并有 producer-owned JSON record。
- Prompt sidecar 采用 UTF-8、LF，并在生成前冻结和 hash。

## 4. Source 处理规则

`01_sources/script/original` 是脚本源证据；其他输入使用
`01_sources/<category>/` 中对应的原始来源目录：

- 不覆盖；
- 不进行无记录重编码；
- 保存原文件字节 SHA-256；
- 每次转换保存 converter identity、输出 hash 和 extraction report；
- 从聊天复制的用户事实也要形成稳定 source ID。

Windows 的 legacy `.doc/.rtf` 不应由系统猜测文本。先在 Word 中另存为 `.docx`，或使用确定性、可记录身份的兼容转换器。原始文件继续保留。

## 5. Project Canon 规则

唯一 Canon 路径：

```text
<PROJECT_ROOT>/00_project_canon/PROJECT_CANON_MANIFEST.json
```

所有 Canon `locator` 和 `artifact_record_locator` 都应为严格 project-relative 路径。这样项目从 Mac 移到 Windows，或从 Windows 移到 Mac 后，只需改变 `<PROJECT_ROOT>`，内容 hash 不因盘符变化而改变。

序列化到 JSON 的 locator 一律使用 POSIX `/` 分隔符，即使当前机器是
Windows；不得写入 `\`、盘符或绝对路径。运行时再由 `Path` 相对
`<PROJECT_ROOT>` 解析。

禁止：

- 在 package 内维护“自己的 current Canon”；
- 在 artifact dependencies 中加入 Canon ID/hash；
- 使用绝对 locator；
- 使用 `..` 穿越项目根；
- 手工覆盖 Project Canon 或伪造 receipt；
- 在一个未完成 transaction 上启动第二个 Owner 写入。

## 6. Windows 与 Mac 之间迁移

### 正确迁移

1. 在源电脑确认没有 `PENDING_PROJECT_CANON_TRANSACTION.json`，所有写入已完成。
2. 关闭正在使用该项目的 Codex 任务和外部写入工具。
3. 复制**完整 Project Root**，不要只复制最新 P2 或某个 package。
4. 在目标电脑先验证源文件、Canon、active artifact records 和 binary hashes。
5. Aggregate-managed 项目用新机器 `<SYSTEM_ROOT>/docs/CODEX_PROMPTS.md`
   的“恢复中断或换电脑”Prompt 恢复；独立工作流按所调用包的恢复合同继续。
6. 仅在验证通过后继续下一阶段。

### 不建议

- 同一 Project Root 在 Mac 与 Windows 上同时写入；
- 依赖 OneDrive/iCloud/网盘的最终一致性来模拟跨电脑文件锁；
- 只同步 JSON，不同步其绑定的图片/视频；
- 修改相对目录布局后不更新并验证 Canon transition；
- 让 Git 自动合并 Project Canon JSON。

本地 `.canon.lock` 只能保护同一文件系统上的进程，不能保证两台电脑通过云盘同步时的分布式互斥。跨设备切换采用“单写者、完整复制、hash readback”。

## 7. Git 与大媒体文件

Skill 仓库适合 Git；每个广告的 Production Project 未必适合直接把所有图片/MP4 推入普通 Git。

建议：

- Skill、文档、schema、validator 进入 Git；
- Production Project 使用受控工作盘或支持大文件的存储；
- 若使用 Git LFS，先验证公司和家庭环境都能完整取回真实二进制，而不是 pointer file；
- Project Canon 只登记真实解码通过的文件 bytes；Git LFS pointer 不能冒充媒体；
- provider API key、session、cookie 和公司凭据绝不写入仓库、Prompt sidecar 或 Canon。

## 8. 一个项目的启动清单

```text
1. 创建短而稳定的 PROJECT_ROOT。
2. 将原始脚本复制到 `01_sources/script/original/`，其他参考放入对应分类；不覆盖原文件。
3. 在 Windows 上把 legacy DOC/RTF 转为 DOCX，同时保存原始文件。
4. 确认本项目实际调用的 Skill 各自可发现，并完成 package-local validation。
5. 验证这些 Skill 实际声明的 Python、Pillow、FFmpeg、ffprobe 和 Image Generation 依赖。
6. 若显式选择 aggregate-managed workflow，再设置 `<SYSTEM_ROOT>`、运行
   aggregate preflight 并使用其 `docs/CODEX_PROMPTS.md` Master Prompt。
7. 让 Shot Director 初始化唯一 Project Canon。
8. 每次只批准明确 artifact/version/hash。
9. P1 前保存当前 provider capability evidence。
10. P2 后由用户在第三方平台生成；把反馈带回 sole-owner return loop。
```
