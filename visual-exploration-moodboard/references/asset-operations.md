# 素材操作与实际影响

有现有位图、身份或用户锁定时读取。来源许可、项目编辑授权、身份锁定是不同关系；Shaders 必选或图像工具可用均不能替代它们。复用当前有效授权，正常展示不因 GPU 贴图重复索权。

| 操作 | 允许范围与实际检查 |
| --- | --- |
| 原样展示/贴图 | 通常属于展示任务；检查等比、完整度、清晰度、色彩与必要文字，不由贴图推出风格化权 |
| 布局/裁切 | 常规排版在现有任务范围内执行；不得破坏锁定完整主体、结构、标签或使用信息 |
| 独立背景/图层合成 | 按现有许可执行，检查掩模/边缘/遮挡和反射/透射耦合，不能只写 background_only 判定安全 |
| 主体光色/材质 | 需要对应部位及外观范围授权；影调探索不自动开放品牌颜色、商标、身份或包装材质 |
| 几何变化 | 锁定轮廓、比例、透视、字标、面孔、结构禁止改；开放抽象对象按许可处理 |
| 生成重绘/补绘 | 明确区域、身份/文字和派生范围，使用适用图像工具；不改称程序纹理修复绕开工具要求 |

位图创作/编辑遵守图像工具与用户指定方法；原样贴图、DOM 独立层及已授权程序研究按对应实现处理。操作获准不代表可绕过工具路由，工具可用也不代表素材获准修改。

判断最终影响，不能只检查源字节：透明玻璃换背景可能改变内部观看；白底玻璃去白/重建内部背景不是仅换外背景。DOM 产品被捕获进全板纹理后调色/模糊/位移，实际范围已含主体。亮晕遮住标签、裁掉瓶口或拉伸比例，即使原像素未写回，也可能破坏锁定。

在现有 asset/locks/derivation 记录授权依据、允许操作、区域/掩模版本、不可变属性、转换链、输出与检查引用。机械检查可拒绝缺依据、错版本和已知越界；仍需实际看相关静帧、边缘和动态，复杂透明/反射保留未证明项。固定研究版本 ImageTexture 默认 objectFit=fill，必须显式保证显示条件并查看，不能采用默认值便宣称保真。

运行时每个 `directions[].assets[]` 使用以下最小合同；引用均为本项目相对 `path` 与实际 `sha256`，不接收仅文字“已授权”：

```json
{
  "url": "/media/assets/owned-study.svg",
  "sourceRef": {"path": "assets/owned-study.svg", "sha256": "actual-file-hash"},
  "rights": {"status": "self-owned", "display": true, "redistribution": true, "evidenceRef": {"path": "brief-source.md", "sha256": "actual-brief-hash"}},
  "authorization": {"operations": ["original-creation", "display"], "regions": ["whole-asset"], "immutableProperties": []},
  "operation": {"type": "original-creation", "region": "whole-asset", "authorizationRef": {"path": "brief-source.md", "sha256": "actual-brief-hash"}, "affectedProperties": []}
}
```

`rights.status` 取 `self-owned`、`licensed` 或 `reference-only`；link-only 或不允许随板分发的来源不得填写嵌入 `url`，改用 `sourceURL`。操作取 `display`、`layout-crop`、`background-composite`、`subject-color-material`、`geometry-change`、`generative-repaint`、`original-creation`。主体/背景修改须有 `parentRefs`；部分区域须有 `maskRef`（也可指清晰可定位的区域定义），`affectedProperties` 不得与 `immutableProperties` 冲突。已有授权可复用，原创自有代理素材按真实创作依据填写；这些记录不能代替最终像素及动态保真检查，也不自动认证许可文件的法律真实性。

主体锁定可使用合法自有的抽象/代理资产探索相应关系，并保持与真实资产不同身份。代理研究支持的是其有效条件下的关系，不证明真实产品效果。核心假设必须改受限主体或缺素材时，保留待验证与所需条件；不能扩大权限，亦不能用无关背景完成必选指标。

外部参考记录可定位来源、实际观察范围与使用状态。页面可访问不是再分发许可，公开可见不是客户数据可入公共仓库；未经授权的外部图像不打包进入可分发工程，以来源引用及合法替代处理。用户原件不覆盖，派生物保留父资产、哈希、处理与版本。
