# Codex Skills

公开维护的个人 Codex Skill 仓库。仓库根目录的 20 个 Skill 都是独立
安装、独立发现、独立调用、独立验证的包；每个包自己的 `SKILL.md` 及其
包内可用的资源、脚本和 validator 是其唯一运行权威。

任何 Skill 都不得把兄弟包、仓库级路由器、固定 checkout、发布回执或聊天
历史作为执行核心能力的前置条件。跨 Skill 组合只能由仓库外的显式编排器
消费各包已经完成并验收的可移植工件。

## 单个 Skill 快速开始

克隆仓库后，只把需要的一个包复制或链接到一个 Codex discovery root。
下例安装 `material-sensitive-product-master-asset-board`。

### macOS / Linux

```bash
git clone https://github.com/qiuranke99/codex-skills.git
mkdir -p "$HOME/.agents/skills"
cp -R codex-skills/material-sensitive-product-master-asset-board \
  "$HOME/.agents/skills/material-sensitive-product-master-asset-board"
requirements="$HOME/.agents/skills/material-sensitive-product-master-asset-board/requirements.txt"
if [ -f "$requirements" ]; then
  python -m pip install -r "$requirements"
fi
```

### Windows PowerShell

```powershell
git clone https://github.com/qiuranke99/codex-skills.git
New-Item -ItemType Directory -Force "$HOME\.agents\skills" | Out-Null
Copy-Item -Recurse -LiteralPath `
  '.\codex-skills\material-sensitive-product-master-asset-board' `
  -Destination "$HOME\.agents\skills\material-sensitive-product-master-asset-board"
$requirements = "$HOME\.agents\skills\material-sensitive-product-master-asset-board\requirements.txt"
if (Test-Path -LiteralPath $requirements) {
  python -m pip install -r $requirements
}
```

重启 Codex 或新建任务后显式调用：

```text
$material-sensitive-product-master-asset-board
```

其他包使用相同方式，只替换目录名；仅当目标包含 `requirements.txt` 时
安装其 Python 依赖。不要在 `.agents/skills` 与 legacy `.codex/skills`
同时暴露同名 Skill。

## Skill 清单

仓库当前维护 20 个独立 Skill；完整的人读清单、用途、canonical path 和
discovery 说明见 [`SKILLS_INDEX.md`](SKILLS_INDEX.md)。每个 Skill 在仓库
根目录只保留一个唯一包目录。

## `frozen-moment-camera-coverage` 的不可变单包发布

该 Skill 使用 package-scoped 发布控制器。控制器只物化该包在已接受 Git
提交中的精确 tree，冻结快照并切换唯一 discovery entry；它不得安装、更新、
检查或签署其他 Skill。

维护者在已推送且验证通过的 `main` 上执行。运行时 Python 使用该包自己的
依赖，不依赖仓库内其他目录：

```powershell
$commit = (git rev-parse origin/main).Trim()
$runtime = Join-Path $env:TEMP 'frozen-moment-camera-coverage-release'
python -m venv $runtime
$python = Join-Path $runtime 'Scripts\python.exe'
& $python -m pip install --disable-pip-version-check -r `
  .\frozen-moment-camera-coverage\requirements.txt
& $python .github/scripts/manage_standalone_skill_release.py sync `
  --repo-root . `
  --python $python `
  --commit $commit `
  --canonical .\frozen-moment-camera-coverage
& $python .github/scripts/manage_standalone_skill_release.py check `
  --repo-root . `
  --python $python `
  --commit $commit `
  --canonical .\frozen-moment-camera-coverage
```

## 验证

先测试仓库级 standalone validator，再在隔离副本中验证全部 20 个包：

```bash
python .github/scripts/test_validate_standalone_skills.py
python .github/scripts/validate_standalone_skills.py \
  --repo-root . --expected-count 20 --timeout 180
python .github/scripts/run_undeclared_standalone_tests.py \
  --repo-root . --timeout 180
```

前一个验证器执行包内已声明的 deterministic test；后一个通用测试门把尚未
声明测试命令、但含 `scripts/test*.py` 的包逐个复制到空 discovery root 后
执行，不使用中央 Skill 清单或兄弟包。

`frozen-moment-camera-coverage` 的发布控制器另有独立测试：

```bash
python .github/scripts/test_manage_standalone_skill_release.py
```

GitHub Actions 在 Ubuntu、macOS 与 Windows 上分别使用 Python 3.11 和
3.12 运行同一套 standalone 验证。CI 证明包结构、隔离边界与确定性测试，
不能替代真实媒体、外部软件、平台权限或人工视觉验收。

## 数据与许可证

客户脚本、私有 brief、身份资料、参考媒体、生产 manifest、storyboard、
keyframe、生成媒体、平台 payload、凭据和密钥不得提交到这个 Public 仓库。

仓库当前未声明开源许可证。Public 可见性不等于授予复用、修改或商业
分发许可；相关权利仍归各内容权利人所有。
