# Codex Skills

公开维护的个人 Codex Skill 仓库。仓库根目录的 16 个 Skill 都是独立
安装、独立发现、独立调用、独立验证的包；每个包自己的 `SKILL.md` 和
包内 validator 是其运行权威。

仓库同时保留一套显式 opt-in 的 **High-Control AI TVC Production
System（高控制全能参考 AI TVC 生产系统）**。它只负责批量安装、兼容性
回归和端到端工作流编排，不是任何单个 Skill 的安装、运行或验收门禁。

![High-Control AI TVC Production SOP](high-control-ai-tvc/assets/high-control-ai-tvc-sop.svg)

## 单个 Skill 快速开始

克隆仓库后，只把需要的一个包复制或链接到一个 Codex discovery root。
下例安装 `material-sensitive-product-master-asset-board`；不需要
`high-control-ai-tvc/`、suite receipt 或其他 Skill 目录。

### macOS / Linux

```bash
git clone https://github.com/qiuranke99/codex-skills.git
mkdir -p "$HOME/.agents/skills"
cp -R codex-skills/material-sensitive-product-master-asset-board \
  "$HOME/.agents/skills/material-sensitive-product-master-asset-board"
python -m pip install -r \
  "$HOME/.agents/skills/material-sensitive-product-master-asset-board/requirements.txt"
```

### Windows PowerShell

```powershell
git clone https://github.com/qiuranke99/codex-skills.git
New-Item -ItemType Directory -Force "$HOME\.agents\skills" | Out-Null
Copy-Item -Recurse -LiteralPath `
  '.\codex-skills\material-sensitive-product-master-asset-board' `
  -Destination "$HOME\.agents\skills\material-sensitive-product-master-asset-board"
python -m pip install -r `
  "$HOME\.agents\skills\material-sensitive-product-master-asset-board\requirements.txt"
```

重启 Codex 或新建任务后显式调用：

```text
$material-sensitive-product-master-asset-board
```

其他包使用相同方式，只替换目录名。不要在 `.agents/skills` 与 legacy
`.codex/skills` 同时暴露同名 Skill。

## 可选：High-Control AI TVC 聚合工作流

这套系统面向高质量广告，不让视频模型仅凭一段文字自由发挥。它把用户
能够提供的粗脚本逐层编译为可验证、可局部返工、可提交给第三方 Omni
视频模型的 P2 全能参考生成包：

```text
Intake → Shot Contract → Canon Assets + Global Look
→ N=N Modular Storyboard → V1 → K1 → P1 → K2 → V2 → P2
→ Third-party Omni generation → User review → Sole-owner return loop
```

核心控制面包括：

- 粗脚本到专业镜头合同，普通导演缺口由 Skill 推断；
- 人物、产品、包装、特殊材质和场景 Canon；
- 全片 Look Core、合法 Look States 与逐镜 Look Delta；
- 脚本 N 镜头对应 N 个独立、可原子替换的故事板画格；
- 整片节奏 V1、逐镜 K1、generation-unit P1、跨段 K2、动态 V2；
- Seedance 2.5-first 语义、Seedance 2.0 capability-aware render、完整
  references/bindings/payload/lockfile；
- 用户看完候选视频后，问题只返回唯一事实 Owner，并精确失效下游。

系统只使用 `omni_reference_to_video` / all-reference / multimodal
reference-to-video。明确排除 T2V、经典单图 I2V、首尾帧和端点插值。

本仓库的生产终点是 **P2 Provider-ready Package**。实际付费视频任务、
音乐、最终剪辑、调色和独立成片 QC 不属于本系统。

如果用户明确需要整套广告生产链，才进入 `high-control-ai-tvc` 使用批量
安装器、聚合 preflight、SOP 和阶段 Prompt：

克隆仓库后进入 `high-control-ai-tvc`：

### macOS

```bash
git clone https://github.com/qiuranke99/codex-skills.git
cd codex-skills/high-control-ai-tvc
./tools/setup-runtime.sh
./tools/install.sh install
./tools/install.sh audit --automatic-only
```

### Windows PowerShell

```powershell
git clone https://github.com/qiuranke99/codex-skills.git
Set-Location codex-skills\high-control-ai-tvc
.\tools\setup-runtime.ps1
.\tools\install.ps1 install
.\tools\install.ps1 audit -AutomaticOnly
```

该可选路径批量安装 15 个兼容 Skill。安装器使用当前官方用户级 discovery root
`$HOME/.agents/skills`，同时检测 legacy `$HOME/.codex/skills` 中的同名
入口，避免双重发现。已有旧入口必须显式审计/接管或迁移，安装器不会
静默覆盖。

安装完成后重启 Codex 或新建任务，可显式测试：

```text
$ai-video-shot-script-director
```

随后用 [Codex 指令集](high-control-ai-tvc/docs/CODEX_PROMPTS.md) 的
Master Prompt 从粗脚本开始。真实客户项目应位于本 Public 仓库之外。

## Skill 清单

仓库当前维护 16 个独立 Skill；完整人读清单见
[`SKILLS_INDEX.md`](SKILLS_INDEX.md)。

[`high-control-ai-tvc/SUITE_MANIFEST.json`](high-control-ai-tvc/SUITE_MANIFEST.json)
只描述可选聚合 profile 的 15 个兼容成员，不是单 Skill 安装或运行权威。

### 核心 13 个

六个生产流程 Skill：

- `ai-video-shot-script-director`
- `ai-video-global-look-lock`
- `ai-video-modular-storyboard`
- `ai-video-timed-animatic-previs-director`
- `ai-video-keyframe-continuity-pack`
- `ai-video-omni-reference-prompt-director`

七个 Canon Asset Owner：

- `character-casting-lock-board`
- `character-final-lock-board`
- `single-face-character-lock-board`
- `multi-angle-product-identity-lock-board`
- `packaging-product-identity-label-lock-board`
- `material-sensitive-product-master-asset-board`
- `scene-canon-asset-pack`

### 可选探索 2 个

- `cinematic_shot_image_explorer`
- `cinematic_world_builder`

上述 15 个 Skill 以及独立的
`complex-product-identity-reconstruction-asset-locking` 在仓库根目录各
保留一个唯一包目录。任何包的核心能力都不得依赖 sibling 目录；跨 Skill
组合由显式选择的外部编排层消费各包已经完成并验收的工件。

## 文档入口

- [完整 SOP](high-control-ai-tvc/docs/SOP.md)
- [节点、工具、输入与输出](high-control-ai-tvc/docs/TOOLS_INPUTS_OUTPUTS.md)
- [Codex Master / 阶段 / 返工 Prompt](high-control-ai-tvc/docs/CODEX_PROMPTS.md)
- [审批、失效与唯一 Owner 回路](high-control-ai-tvc/docs/REVISION_AND_APPROVAL.md)
- [项目目录与跨设备迁移](high-control-ai-tvc/docs/PROJECT_STRUCTURE.md)
- [跨平台安装、更新与卸载](high-control-ai-tvc/docs/INSTALLATION.md)
- [Windows 指南](high-control-ai-tvc/docs/WINDOWS.md)
- [macOS 指南](high-control-ai-tvc/docs/MACOS.md)
- [客户数据与密钥边界](high-control-ai-tvc/docs/SECURITY_AND_DATA.md)
- [来源与同步边界](high-control-ai-tvc/docs/SOURCE_PROVENANCE.md)

## 可选聚合工作流的运行依赖

- Python 3.11 或 3.12；
- 精确 `Pillow==11.3.0`；
- FFmpeg、ffprobe 与 `libx264`；
- Codex 本地文件访问和 Image Generation；
- 复杂 V2 所需的 Prevzi、Blender 或等价 2D/3D control-previs 路径；
- 目标第三方平台的真实 Omni 表面、账号权限和 hash-bound capability
  snapshot。

Windows legacy `.doc/.rtf` 不是可移植输入；先用 Word 或受信任转换器
另存为 `.docx`，保留原始字节。脚本内容仍可保持粗糙、写意；这只是
格式转换，不要求用户补专业导演语言或产品功能说明。

## 验证

先运行与 High-Control 无关的 16 包独立性验证：

```bash
python .github/scripts/validate_standalone_skills.py --repo-root .
```

只有在修改或采用可选聚合 profile 时，再运行：

```bash
python high-control-ai-tvc/tools/validate_distribution.py
python high-control-ai-tvc/tools/preflight.py --repository-only --format json
python high-control-ai-tvc/tools/validate_ai_video_aggregate.py --suite-root .
```

GitHub Actions 在 Ubuntu、macOS 与 Windows 上验证 Python 3.11/3.12、
16 包独立性、可选 15 包聚合兼容性、安装生命周期和 PowerShell/POSIX
语法。真实工作站
仍须通过本机完整 preflight；CI 不能替代 Image Generation、V2 工具或
第三方 provider 权限的人工确认。

## 数据与许可证

客户脚本、参考图、Canon、关键帧、控制视频、P2 payload 和密钥不得
提交到这个 Public 仓库。详见
[客户数据与密钥边界](high-control-ai-tvc/docs/SECURITY_AND_DATA.md)。

仓库当前未声明开源许可证。Public 可见性不等于授予复用、修改或商业
分发许可；相关权利仍归各内容权利人所有。
