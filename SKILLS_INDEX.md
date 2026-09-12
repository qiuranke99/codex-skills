# Codex Skills Index

更新日期：2026-09-12。以下是 [SKILLS_MANIFEST.json](SKILLS_MANIFEST.json) 记录的17个当前源码包，路径相对于本仓库。本索引不宣称所有源码都已安装。

清单只描述源码库存，不构成业务或视觉验收。运行方式和维护校验见 [README.md](README.md)。

| Skill | 用途 |
| --- | --- |
| [advertising-reference-research-director](advertising-reference-research-director/SKILL.md) | 正式广告图像/视频参考研究与真实媒体核验 |
| [ai-video-global-look-lock](ai-video-global-look-lock/SKILL.md) | 全片影调、Look Core、状态与逐镜差异 |
| [ai-video-keyframe-continuity-pack](ai-video-keyframe-continuity-pack/SKILL.md) | K1关键帧与可选K2边界补充 |
| [ai-video-modular-storyboard](ai-video-modular-storyboard/SKILL.md) | 逐镜独立分镜、审阅包与局部替换 |
| [ai-video-shot-script-director](ai-video-shot-script-director/SKILL.md) | 粗脚本转专业镜头合同 |
| [ai-video-timed-animatic-previs-director](ai-video-timed-animatic-previs-director/SKILL.md) | V1时序预演与有证据支持的V2控制预演 |
| [character-casting-lock-board](character-casting-lock-board/SKILL.md) | 人物选角与候选身份板 |
| [character-final-lock-board](character-final-lock-board/SKILL.md) | 最终人物身份、服装与多角度资产板 |
| [cinematic_shot_image_explorer](cinematic_shot_image_explorer/SKILL.md) | 按用户数量和输出模式探索电影镜头 |
| [complex-product-identity-reconstruction-asset-locking](complex-product-identity-reconstruction-asset-locking/SKILL.md) | 复杂产品身份、结构与状态锁定 |
| [frozen-moment-camera-coverage](frozen-moment-camera-coverage/SKILL.md) | 同一冻结瞬间多机位覆盖；独立不可变发布 |
| [material-sensitive-product-master-asset-board](material-sensitive-product-master-asset-board/SKILL.md) | 材质敏感产品资产板 |
| [multi-angle-product-identity-lock-board](multi-angle-product-identity-lock-board/SKILL.md) | 低风险产品六视图几何身份板 |
| [packaging-product-identity-label-lock-board](packaging-product-identity-label-lock-board/SKILL.md) | 包装身份、标签与来源文字资产板 |
| [product-tvc-30s-director](product-tvc-30s-director/SKILL.md) | 综合30秒产品TVC提示词；仅文本 |
| [product-tvc-lighting-director](product-tvc-lighting-director/SKILL.md) | 照明主导TVC与锁定镜序灯光升级；仅文本 |
| [single-face-character-lock-board](single-face-character-lock-board/SKILL.md) | 单一可见人脸及无头正背面服装板 |

## 安装与调用

每包可独立复制或链接到用户 `.agents/skills`；已有 legacy `.codex/skills` 安装需避免重复发现。当前机器状态以实际发现结果为准，不再保留过期机器快照或待安装表。

普通产品提示词与照明主导提示词选择对应主入口，不因共用规则加载两包。项目集成是用户显式选择的外部产物交换，不构成单包完成前置条件。产品事实、真实证据、锁定内容和人工批准边界由各包合同定义。

## 不纳入当前清单

已删除Skill的源码、退役聚合系统、旧副本、供应商插件缓存、系统技能、运行时环境、客户项目和维护输出不在当前清单内。blender-production-governor、reference-guided-image-reconstruction-director 与 high-control-ai-tvc 旧目录已移除。历史变更保留于Git历史，不恢复成可发现入口。
