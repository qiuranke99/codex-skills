# 来源与同步边界

本 High-Control AI TVC 子系统最初在
[`qiuranke99/codex-skills`](https://github.com/qiuranke99/codex-skills)
以下 provenance 基线提交之上建立：

```text
cd72953b283b52b83e144e3e82d40e59d3275bdd
```

权威清单位于根目录 `SUITE_MANIFEST.json`：

- 6 个新建 AI 视频 SOP Skill；
- 7 个更新后的 Canon Asset Owner Skill；
- 2 个可选电影镜头/世界探索 Skill；
- 合计 15 个唯一顶层 Skill。

`independent_skills` 另声明
`complex-product-identity-reconstruction-asset-locking`。它不改变 15-skill
High-Control 业务计数，但属于同一 GitHub publication release，不能继续
指向本机 authoring checkout。

首个系统化批次保持 15 个现有 Skill 目录不重复、不另复制，也不为了
安装便利改写 Skill 合同。跨平台安装、文档、流程图和验证能力集中在
仓库的 `high-control-ai-tvc/` 子目录，并从那里引用根级 Skill。

该基线不是当前 release 指针。包含自身的 tracked manifest 无法稳定保存
“包含该字段的当前 commit”，因此 `source_commit` 已被禁止；实际发布 OID
只写入仓库外的 release receipt。

跨机生产权威合同：

1. GitHub repository id `1264973746`、`qiuranke99/codex-skills`、
   `refs/heads/main` 共同定义唯一发布面；Windows/Mac checkout 都只是
   authoring workspace。
2. `release_control.py sync` 在线双读远端，抓取精确 OID，从 Git object
   字节建立 `releases/<OID>/repo`，运行完整验证，再原子激活 discovery。
3. 15 个 suite Skill 与 manifest 声明的独立 Skill 只能从同一个已验证
   不可变 snapshot 被生产调用；receipt 绑定
   repository、commit、Git tree、manifest、runtime requirements、每个 Skill
   tree 和安装回执。
4. 每个生产阶段入口重新运行 `check`。远端更新、离线、摘要漂移、重复
   discovery、并发更新或当前进程缓存旧合同都会 fail closed。
5. GitHub 最新提交验证失败时不得静默回退旧 release。旧 snapshot 可留作
   取证，但状态必须是 `NOT_READY_LATEST`。

`codex-skills` 是唯一远端发布面；不得建立同内容的第二个 GitHub 仓库、
fork authority 或第二套顶层 Skill。
