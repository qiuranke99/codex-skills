# Codex Skills

公开维护的个人 Codex Skill 源码仓库。当前保留 **17 个独立包**，每包只维护一个当前版本。机器清单为 [SKILLS_MANIFEST.json](SKILLS_MANIFEST.json)，用途索引为 [SKILLS_INDEX.md](SKILLS_INDEX.md)。源码存在不等于已在某台机器安装。

机器清单描述源码库存，不是安装、视觉或生产批准回执。

原 High-Control 聚合系统已退役，旧批量安装器、聚合发布门和 SOP 已移除；CI 只验证独立包。不恢复被删除的技能，不把旧聚合流程作为独立包的使用前提。历史版本仅从 Git 历史追溯，不在当前树保留旧副本。

## 安装普通独立包

克隆仓库后，只把需要的包复制或链接到用户的 `.agents/skills`。例如：

```bash
git clone https://github.com/qiuranke99/codex-skills.git
mkdir -p "$HOME/.agents/skills"
cp -R codex-skills/material-sensitive-product-master-asset-board "$HOME/.agents/skills/"
python -m pip install -r "$HOME/.agents/skills/material-sensitive-product-master-asset-board/requirements.txt"
```

Windows PowerShell：

```powershell
git clone https://github.com/qiuranke99/codex-skills.git
New-Item -ItemType Directory -Force "$HOME\.agents\skills" | Out-Null
Copy-Item -Recurse -LiteralPath '.\codex-skills\material-sensitive-product-master-asset-board' -Destination "$HOME\.agents\skills"
python -m pip install -r "$HOME\.agents\skills\material-sensitive-product-master-asset-board\requirements.txt"
```

以上用于首次安装。更新已有安装前比较源文件，避免覆盖本地修改；不要同时在 `.agents/skills` 和 legacy `.codex/skills` 暴露同名 Skill。实际依赖以该包的 requirements 为准，安装依赖需要用户授权。每包自己的 `SKILL.md` 定义输入、边界、引用和完成条件，不需仓库级运行门。

## Frozen Moment 的独立不可变发布

`frozen-moment-camera-coverage` 保留包级不可变发布控制器。普通源码同步不自动切换已安装 release，也不修改只读快照。仅在明确发布该包时运行：

```powershell
$commit = (git rev-parse origin/main).Trim()
$pythonExecutable = (Get-Command python -CommandType Application).Source
python .github/scripts/manage_standalone_skill_release.py sync --repo-root . --python $pythonExecutable --commit $commit --canonical .\frozen-moment-camera-coverage
python .github/scripts/manage_standalone_skill_release.py check --repo-root . --python $pythonExecutable --commit $commit --canonical .\frozen-moment-camera-coverage
```

使用具备该包依赖的真实 Python 可执行文件。控制器仅物化目标包的精确 Git tree，验证字节、只读保护、唯一 discovery 与包测试；不安装或签署其他包，不依赖全库库存作为发布门。当前回执使用包级 v2；历史 v1 仅用于受校验的迁移和恢复，不直接当作当前通过回执。源码同步不会自动切换已安装 release。测试通过不等于视觉批准。

## 维护与验证

修改一个 Skill 时运行相关检查；跨包维护需发现并验证全部当前包：

```bash
python .github/scripts/test_validate_skill_inventory.py
python .github/scripts/validate_skill_inventory.py --repo-root . --expected-count 17
python .github/scripts/test_validate_standalone_skills.py
python .github/scripts/test_run_undeclared_standalone_tests.py
python .github/scripts/test_manage_standalone_skill_release.py
python .github/scripts/validate_standalone_skills.py --repo-root . --expected-count 17 --timeout 180 --compact
python .github/scripts/run_undeclared_standalone_tests.py --repo-root . --timeout 180
```

CI 配置覆盖 Ubuntu、macOS、Windows 的 Python 3.11/3.12；包含源库存、隔离、发布安全与恢复、未声明包内测试及 PowerShell/POSIX 入口检查。Previs 的真实微视频回归需要 PATH 中可用的 FFmpeg 和 ffprobe；它们不是退役聚合系统依赖。各平台的实际通过状态以对应 CI 回执为准。隔离验证与离线测试不能证明真实生成结果、产品文字准确率、媒体权限或用户已经批准。

## 数据边界

仅发布可复用 Skill、通用代码、合成测试和文档。客户脚本、原图、人物身份素材、实际项目、模型输出、访问凭证、浏览器状态和本机运行回执不得进入本公开仓库。实际项目与维护证据放在仓库外。源码发布不授权业务操作、付费生成、账户变更或现有安装的自动切换。
