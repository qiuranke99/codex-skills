# High-Control AI TVC Production System

`codex-skills` 内的高控制全能参考 AI TVC 生产子系统。15 个唯一 Skill
仍位于仓库根目录；本目录只保存统一清单、SOP、流程图、安装器和预检，
不复制 Skill，也不保存客户项目。

![完整生产 SOP](assets/high-control-ai-tvc-sop.svg)

## 生产终点

```text
粗脚本与证据
→ Professional Shot Contract
→ Canon Assets + Global Look
→ N=N Modular Storyboard
→ V1 → K1 → P1 → K2 → V2 → P2
→ 第三方 Omni 生成
→ 用户审片 → 唯一 Owner 精确返工
```

本系统终点是可提交的 P2 Provider-ready Package。实际付费视频生成、
音乐、最终剪辑、调色和独立成片 QC 均在范围之外。

禁止替代为：T2V、经典单图 I2V、首尾帧或 endpoint-frame
interpolation。角色、产品、场景、影调、故事板、关键帧和控制预演均作为
普通并行参考进入 Omni / all-reference / multimodal reference-to-video。

## 安装

从本目录运行：

macOS：

```bash
./tools/setup-runtime.sh
./tools/install.sh install
./tools/install.sh audit --automatic-only
```

Windows PowerShell：

```powershell
.\tools\setup-runtime.ps1
.\tools\install.ps1 install
.\tools\install.ps1 audit -AutomaticOnly
```

如果旧版安装已经通过 `.codex/skills` 精确链接到当前 checkout，先运行
显式 `adopt`，不要手工复制或双挂到 `.agents/skills`。完整的 adopt、
migrate、update 和 uninstall 规则见 [安装文档](docs/INSTALLATION.md)。

## 从项目开始

真实客户项目必须放在本 Public 仓库之外。可以安全创建一个不含假 Canon
和客户素材的目录骨架：

```bash
./tools/new-project.sh "/path/to/client projects/bath-oil-tvc" --name "Bath Oil TVC"
```

```powershell
.\tools\new-project.ps1 -Destination "D:\Client Projects\Bath Oil TVC" -Name "Bath Oil TVC"
```

随后在 Codex 中打开该项目目录，使用
[Codex 指令集](docs/CODEX_PROMPTS.md) 的 Master Prompt。

## 文档

- [完整 SOP](docs/SOP.md)
- [工具、节点、输入与输出](docs/TOOLS_INPUTS_OUTPUTS.md)
- [Codex Master / 阶段 / 返工 Prompt](docs/CODEX_PROMPTS.md)
- [审批与唯一 Owner 返工](docs/REVISION_AND_APPROVAL.md)
- [项目目录与跨设备迁移](docs/PROJECT_STRUCTURE.md)
- [安装、更新、接管、迁移与卸载](docs/INSTALLATION.md)
- [Windows](docs/WINDOWS.md) / [macOS](docs/MACOS.md)
- [客户数据与密钥边界](docs/SECURITY_AND_DATA.md)
- [来源与同步边界](docs/SOURCE_PROVENANCE.md)

## 验收

从 `codex-skills` 仓库根运行：

```bash
python high-control-ai-tvc/tools/validate_distribution.py
python high-control-ai-tvc/tools/preflight.py --repository-only --format json
python high-control-ai-tvc/tools/test_install_lifecycle.py
python ai-video-omni-reference-prompt-director/scripts/validate_ai_video_suite.py --suite-root .
```

真实机器必须再通过完整 preflight，并人工确认 Codex Image Generation、
复杂 V2 制作路径和目标第三方 Omni 平台权限。
