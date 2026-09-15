# 交付记录与检查器

检查器仅依赖Python 3.11+标准库，只读项目文件，不生成媒体、不更改批准状态、不联网。本文件规定记录格式，不能用记录本身代替实际制作或查看。

## 使用顺序

1. 在真实业务项目保存原始需求、有效输入及成品。需要便携交接时，将获准使用的必要文件复制到项目包；不能把客户数据放入Skill源码仓库。
2. 从assets/contract.template.json建立contract.json。按原始要求填写所需成品，不以已经生成的数量反推需求。
3. 制作、实际检查、修正和最终导出。保存探测工具输出与视觉检查证据；根据已观察事实填写记录，禁止编造观看、播放、批准或首评。
4. 从assets/delivery.template.json建立delivery.json，为每项填写实际文件与对应记录。
5. 运行检查，解决错误，完成成品交接。空模板有意不能通过检查。

从已安装Skill目录执行，项目路径替换为实际位置：

~~~text
python scripts/check_delivery.py hash <实际文件>
python scripts/check_delivery.py inputs-digest --root <项目目录> --output-id KV-01
python scripts/check_delivery.py check --root <项目目录>
~~~

所有记录中的文件引用均为项目内相对路径和小写SHA256。不能使用绝对路径、上级路径或指向项目外的符号链接；移动整包不会改变记录含义。

## contract.json

顶层字段：

- schema_version固定为brand-delivery-contract.v1。
- project为真实项目名。
- independent_review_required、user_review_required为布尔值，来自实际用户要求及适用流程。
- inputs为非空输入清单；每项含id、role、status、path、sha256。role至少说明brief、product、brand、campaign或scene等实际职责。status为provided、approved或rejected；rejected输入可作历史记录，但不得成为成品的活动输入。
- requirements为非空所需成品清单。每项具有唯一id、kind、purpose、source_input_ids、contains_text、required_checks和spec。

成品示例结构（示例不表示已制作）：

~~~json
{
  "id": "KV-01",
  "kind": "image",
  "purpose": "已约定用途的主视觉",
  "source_input_ids": ["original-brief", "brand-assets", "product-front"],
  "contains_text": true,
  "required_checks": ["brand", "product", "copy", "craft", "composition"],
  "spec": {"width": 1080, "height": 1350, "extension": ".png"}
}
~~~

kind可为image、video、document、source。image/video须有正整数width和height，video还须有duration秒数。其他spec可声明页数、帧率、音轨或可编辑性等实际要求，必须有对应技术探测结果。数值比较只允许序列化级误差；需要帧级时长时填写实际所需帧数对应的时长，不以模糊百分比放宽要求。

每项必须引用原始brief输入。图像、文档和视频至少检查brand、craft、composition；包含产品输入时增加product；含文字时增加copy；视频增加motion；源文件检查editability。其余检查依据实际需要添加，不能为了通过而删除问题项。

同一文件内容默认不能冒充不同成品。确实允许多个用途共享同一文件时，在相关requirements上明确allow_shared_artifact=true，并保留这一需求依据。

## 技术记录

每项成品保存独立JSON：

~~~json
{
  "artifact_sha256": "实际成品的64位小写SHA256",
  "passed": true,
  "method": "实际使用的解码、渲染、探测或打开工具及方法",
  "observed": {"width": 1080, "height": 1350, "extension": ".png"}
}
~~~

observed必须来自真实工具输出。先实际解码/打开文件再记passed，不以文件后缀推断成功。所有spec字段都需与observed一致。检查器会额外核对PNG头部尺寸；其他媒体的属性来自已绑定技术记录，仍须执行实际探测、渲染和播放。

## 视觉/内容检查记录

每项保存独立JSON，至少含：

- kind=self或independent；reviewer为真实审阅者身份。
- artifact_sha256为当前成品哈希，inputs_digest来自本包命令。
- method：图片visual，视频playback_full，文档rendered_pages，源文件opened_source。
- recorded_at：含时区的ISO时间。
- checks：键为检查项，每项含result和具体observation；result只允许pass、fail、unverified。
- evidence：非空文件引用数组，绑定实际检查截图、播放/渲染记录或观察记录；内容须支持判定。
- limitations：未解决问题数组，全部解决时为空。

独立审阅额外绑定first_review文件。首评包含kind=first_independent_review、同一reviewer、artifact_sha256、inputs_digest、recorded_at、checks、evidence、limitations，并声明participated_in_production=false、exposure=none。首评时间早于最终对照；检查结论变化时，最终对应项增加change_reason及复核依据。采用环境已有封存协议时同时遵守，不能用这些字段冒充真实封存或清除已经发生的暴露。

输入摘要按本项的需求、相关输入及独立审阅要求计算。相关资料改变后，旧输出或旧审阅摘要会失败；不相关输入变化不会强迫无关成品重做。contract文件自身仍需重新绑定，保证完整交付使用当前约定。

## delivery.json

- schema_version固定为brand-delivery-manifest.v1。
- contract引用实际contract.json及其哈希。
- outputs必须与requirements逐项对应。每项含id、creator、file、inputs_digest、technical、review；file、technical、review均为path与sha256引用。
- user_acceptance.status为not_requested、pending或accepted。要求用户审阅时不得写not_requested；自检不自动改为accepted。

如记录accepted，另附record文件引用。该JSON包含真实approved_by、source（用户批准的原始出处）、当前contract_sha256、accepted_outputs（成品ID到当前哈希的完整映射）。程序只能核对记录及版本，无法鉴别人或批准出处，执行者仍须实际读取授权证据。

退出码0表示文件、版本、完整性和所填记录相互一致。它不表示视觉已被程序验证，也不等于用户已批准。用户审阅pending时可完成文件交付，但必须保留这个状态。任何关键检查fail、unverified、缺证据或缺成品均返回非零退出码。
