# 来源与同步边界

本 High-Control AI TVC 子系统在
[`qiuranke99/codex-skills`](https://github.com/qiuranke99/codex-skills)
以下不可变基线提交之上建立：

```text
cd72953b283b52b83e144e3e82d40e59d3275bdd
```

权威清单位于根目录 `SUITE_MANIFEST.json`：

- 6 个新建 AI 视频 SOP Skill；
- 7 个更新后的 Canon Asset Owner Skill；
- 2 个可选电影镜头/世界探索 Skill；
- 合计 15 个唯一顶层 Skill。

首个系统化批次保持 15 个现有 Skill 目录不重复、不另复制，也不为了
安装便利改写 Skill 合同。跨平台安装、文档、流程图和验证能力集中在
仓库的 `high-control-ai-tvc/` 子目录，并从那里引用根级 Skill。

后续从上游同步时必须：

1. 固定上游 commit，不从浮动分支直接发布；
2. 依据 `SUITE_MANIFEST.json` 比较 Skill 集合；
3. 拒绝重复名称、缺失 sibling dependency 或未经审阅的合同变化；
4. 更新 source commit、版本和 Changelog；
5. 重跑完整 suite tests、安装预检和 fresh-clone 验收。

`codex-skills` 是唯一远端发布面；不得再建立同内容的第二个 GitHub
仓库或第二套顶层 Skill。
