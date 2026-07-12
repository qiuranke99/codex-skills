# Changelog

## 1.0.0 — 2026-07-12

- 无重复聚合 15 个 Codex Skill：6 个新 SOP Skill、7 个核心 Canon
  Asset Owner 和 2 个可选 cinematic explorer；
- 建立从粗脚本到 P2 Provider-ready Package 的高控制 Omni-reference
  AI TVC SOP；
- 增加完整流程图、跨平台安装/预检、Codex 启动提示和项目数据边界；
- 安装采用全量预暂存、receipt 原子提交与失败回滚；卸载可从中途失败
  安全恢复，并拒绝 state/discovery 重定向与非隔离 Python 运行时；
- GitHub Actions 覆盖 Ubuntu、macOS、Windows 与 Python 3.11/3.12，动态
  验证安装、完整 automatic audit、项目骨架、runtime 和卸载生命周期；
- 所有 Canon/package locator 统一序列化为 POSIX project-relative 路径，
  文本、提示词证据与机器收据固定为 UTF-8/LF，确保 Windows/Mac 可迁移；
- 六 Skill 集成验证器固定以 UTF-8 启动并解码子验证器，避免 Windows
  legacy console codec 在报告中文路径或合同术语时中断；
- CI 使用 Node 24 代际的 checkout/setup-python Action，移除已弃用
  Node 20 Action runtime；
- 流程图明确区分仓库生产终点 P2 与仓库外部的用户审片闭环终点；
- Keyframe/Boundary 文件定位器强制 portable POSIX project-relative 语法，
  拒绝反斜杠、盘符、绝对路径与 traversal；
- Windows CI 直接在 Windows PowerShell 5.1 下验证 copy-mode 安装生命周期
  与 pinned runtime setup；
- 固定来源提交
  `cd72953b283b52b83e144e3e82d40e59d3275bdd`；
- 保持实际视频 API 提交、音乐、剪辑、调色和独立 QC 在系统范围之外。
