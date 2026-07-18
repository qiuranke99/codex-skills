# Changelog

## Unreleased — 2026-07-18

- `material-sensitive-product-master-asset-board` 升级到 v5：从真实历史使用中
  识别并移除手工拼接 QA、4K handoff 与 accepted attempt 的剩余维护面；新增
  来源对板决策 scaffold、`material_board_qa.v3` 确定性冻结器，以及先全量
  preflight、最后写 accepted commit 的后生图编译器；final builder 独立重放
  worker rollout，并逐字节重渲染 QA、4K prompt、handoff 和 accepted record；
  单包仍不依赖 High-Control。
- 可选聚合验证器将根级 standalone validator 的单包上限显式设为 180 秒，
  避免声明了较长确定性测试的独立包被 30 秒 CLI 默认值误判为无效配置。
- GitHub 的 standalone authority job 现在从 material 单包自己的
  `requirements.txt` 安装 Pillow，再运行其声明的隔离确定性测试。

## 2.0.0 — 2026-07-18

- 将仓库根目录 16 个 Skill 确立为独立安装、发现、调用和验证的包；移除
  单包 `SKILL.md` 对 release gate、suite receipt、聚合 launcher、固定 suite
  runtime 与 sibling package 的强制依赖；
- High-Control 改为显式 opt-in 的 15-Skill 聚合兼容、批量安装、不可变发布
  与端到端编排层；其 receipt 和 readiness 不再决定任何单包 availability；
- 增加标准库实现的 16 包 standalone validator：逐包复制到空 discovery
  root，清空环境路径，检查元数据、外链、越界路径、兄弟包 import 与 Python
  编译，并提供稳定错误码和非变异反例；
- 将七个资产 Owner 与六个 workflow Writer 共用的 Project Canon 原子事务桥
  迁入可选聚合工具，保留全局锁、pending journal、崩溃恢复、CAS、批准/
  哈希/媒体验证与传递 stale 传播，不再在单包内保留 sibling wrapper；
- `material-sensitive-product-master-asset-board` 升级到 v4：完整解码 source
  bundle、source semantics/invariant/panel contract、确定性 worker exec、whole-
  rollout 绑定、逐 panel/invariant QA、确定性 4K prompt renderer、外部状态矩阵
  与 40 项正反例；历史 topology-drift board 只保留为红样本；
- CI 分离 16 包 standalone authority 与可选 aggregate compatibility，后者继续
  覆盖 Python 3.11/3.12、Ubuntu/macOS/Windows、安装生命周期、发布回滚、
  schema parity、Canon transaction 和 PowerShell/POSIX 语法。

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
- Prompt/P1 合同负例改为顺序隔离夹具：Packaging 权威闭包由预写审计门
  冻结，非 Packaging 变更按 byte/path/stat 回滚；保留 180 秒单测上限，
  POSIX 进程组与 Windows Job Object 确保超时后无孤儿子进程；
- 16 个生产 Skill 的 release gate 统一改用 OS-native launcher；launcher 从
  已验证 release receipt 解析固定 Python，并先离开活动 snapshot 再执行
  check/sync，避免全局 Python 缺失、依赖漂移或 Windows 当前目录锁定；
- GitHub commit snapshot 在激活前获得操作系统级只读保护：Windows 递归
  current-user RX ACL，macOS/Linux 清除全部写位；production check 实际证明
  新建文件与现有文件写句柄均被拒绝，并继续逐 Git blob 反证篡改；
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
