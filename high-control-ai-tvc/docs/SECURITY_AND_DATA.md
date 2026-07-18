# 客户数据与密钥边界

这个仓库是公开的生产系统源码，不是客户项目存储区。

这些数据边界同时适用于独立 Skill 和显式选择的 aggregate workflow；
`high-control-ai-tvc` 的 receipt、release gate 或 preflight 不决定单包是否
available，也不会取得客户数据的管理权。

## 必须放在仓库之外的内容

- 客户粗脚本、品牌策略和未发布创意；
- 人物、产品、包装、场景和风格参考原图；
- Project Canon、Storyboard、Keyframe、V1/V2 和 P2 运行产物；
- Seedance、Kling 或第三方平台的请求 payload、返回值和账户信息；
- API key、Cookie、访问令牌、证书、私钥和 `.env` 文件；
- 任何受保密协议、肖像权、商标权或素材许可证约束的文件。

建议把真实项目放在独立目录，例如：

```text
~/AI-TVC-Projects/<client-or-campaign>/
C:\AI-TVC-Projects\<client-or-campaign>\
```

Codex 项目应打开真实项目目录，而不是把客户素材复制进这个 Public
仓库。Skill 通过用户级 discovery 链接被调用，无需把 Skill 再复制进
客户项目。

## 第三方模型上传前

1. 确认人物、产品、品牌素材及任何 source-approved dialogue/SFX 的使用权；
2. 检查平台的数据保留、训练使用、区域和企业隐私设置；
3. 删除不属于当前 generation unit 的无关或冲突参考；
4. 不把密钥写入 prompt、JSON manifest、截图或项目日志；
5. 对 provider capability snapshot 只保存能力结构和证据定位，不保存
   登录凭据。

## 公开仓库保护

根 `.gitignore` 已屏蔽常见密钥、环境文件、Project Canon、输出和本地
项目目录，但 `.gitignore` 不是安全边界。提交前仍应运行根验证器并
人工检查 `git diff --cached`。
