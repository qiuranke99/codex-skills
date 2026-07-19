# 来源与同步边界

本 High-Control AI TVC 子系统最初在
[`qiuranke99/codex-skills`](https://github.com/qiuranke99/codex-skills)
以下 provenance 基线提交之上建立：

```text
cd72953b283b52b83e144e3e82d40e59d3275bdd
```

根目录 `SUITE_MANIFEST.json` 记录显式 opt-in aggregate compatibility
profile 的清单：

- 6 个新建 AI 视频 SOP Skill；
- 7 个更新后的 Canon Asset Owner Skill；
- 2 个可选电影镜头/世界探索 Skill；
- 合计 15 个唯一顶层 Skill。

`excluded_from_aggregate_profile` 声明
`advertising-reference-research-director` 与
`complex-product-identity-reconstruction-asset-locking`、
`frozen-moment-camera-coverage` 只被当前 aggregate profile 排除，因此仓库共有
18 个 standalone 顶层 Skill。该字段只是聚合
范围边界：批量工具必须验证这些包存在，但不得管理它们、写入安装或发布
回执；它也不把其余 15 个包变成 High-Control 的从属包。

首个系统化批次保持现有 Skill 目录不重复、不另复制，也不为了安装便利
改写 Skill 合同。每个顶层包独立拥有自身安装、发现、调用和验证权威。
可选的跨平台批量安装、文档、流程图和聚合验证能力集中在仓库的
`high-control-ai-tvc/` 子目录，并从那里引用根级 Skill。

该基线不是当前 release 指针。包含自身的 tracked manifest 无法稳定保存
“包含该字段的当前 commit”，因此 `source_commit` 已被禁止；实际发布 OID
只写入仓库外的 release receipt。

单包来源合同：

1. 每个顶层 Skill 可从其自身包直接复制或链接到 discovery root；其
   `SKILL.md`、package-local resources 和 validator 决定该包是否可用。
2. 单包不要求 suite manifest、aggregate receipt、release-control launcher、
   pinned runtime、兄弟目录或与其他 Skill 位于同一 revision。
3. GitHub commit/tree/blob 证据可用于验证某个包的不可变来源，但远端出现
   更新是 `update_available`，不是既有 hash-valid 单包失效。

`frozen-moment-camera-coverage` 另有仓库级 package-scoped 控制器
`.github/scripts/manage_standalone_skill_release.py`。它只为该排除包建立精确
Git tree 的只读快照、单包回执与唯一 discovery 入口；该回执明确
`controls_aggregate_members=false`，不得被 aggregate 工具消费。

显式 aggregate-managed workflow 的跨机维护合同：

1. GitHub repository id `1264973746`、`qiuranke99/codex-skills`、
   `refs/heads/main` 共同定义 aggregate snapshot 的更新面。
2. `release_control.py sync` 交叉核验 Git transport 与 GitHub API，抓取精确
   OID，从 Git object 字节建立 `releases/<OID>/repo`，运行完整验证，再原子
   激活用户选择的 aggregate-managed entries。aggregate `check` 使用 GitHub
   API 的 repository identity + branch ref，不依赖 Windows Git/Schannel
   凭据是否可用。
3. 在同一个 aggregate-managed 项目事务内，所选 entries 从同一个已验证
   不可变 snapshot 被调用；receipt 绑定
   repository、commit、Git tree、manifest、runtime requirements、每个 Skill
   tree 和安装回执。该 receipt 只证明 aggregate 管理所有权与兼容性状态，
   不证明或否定单包 availability。
4. 已选择 aggregate-managed workflow 时，每个生产阶段入口重新运行
   `check`。远端更新、离线、摘要漂移、重复 discovery、并发更新或当前进程
   缓存旧合同都会使该聚合工作流 fail closed。
5. Aggregate 最新提交验证失败时不得把旧 release 冒充
   `AGGREGATE_READY_LATEST`。旧 snapshot 可留作取证或精确 readback；其状态不影响
   独立安装且 package-local validation 通过的 Skill。

`codex-skills` 是本维护 profile 的远端发布面；不得把 aggregate receipt 或
fork 声明成任一单包的上位运行权威。
