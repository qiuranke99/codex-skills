# 本地执行与运行契约

本文件描述本包JSON与脚本接口。全部命令在本包目录执行；将示例中的业务目录替换为当前已授权目录。生产输入、生成图片、blend、视频、日志和自评均留在业务目录，不能写进Skill包。

## 1. 依赖与授权

- Python 3.11或更高版本，Blender之外仅用Python标准库。
- 可执行本包Python的Blender后台入口；优先遵守当前环境的后台MCP约定。脚本不打开Blender桌面，不启动浏览器。
- 本地ffmpeg与ffprobe，用于逐镜视频、完整合成和媒体读回；从当前环境发现可执行文件，不假定固定安装路径。
- 正常业务流程需要代理调用已授权图像生成工具生成布局图。Python不提供离线“伪生图”，Runway也不是必装依赖。

先检查工具是否实际可调用；缺少Blender或媒体工具时给出具体缺口，不能把仅通过契约校验称为预演完成。既有授权允许的本地修复可直接完成；不能据Skill调用自行扩张付费、上传或发布范围。

## 2. 创建业务契约

契约为UTF-8 JSON，`schema`为`product-tvc-previs/v1`。路径以该JSON的父目录为根，只接受根内相对路径；禁止绝对路径、`..`越界和符号链接逃逸。资产必须存在且SHA256一致。契约与资产保持在业务目录中，`prepare`将其复制到独立lane。

### 全局字段

| 字段 | 内容 |
| --- | --- |
| `id` | 仅使用安全标识字符的本次契约ID |
| `fixture` | 真实业务为`false`；合成技术案例为`true`，不能伪装成客户制作 |
| `fps` | 整数帧率，1—120；制作时按用户要求选择 |
| `duration_frames` | 正整数，全片总帧数；秒数为帧数除以`fps` |
| `resolution` | `[width, height]`，正偶数像素；低分辨率只用于相应预览 |
| `hold_start` | 全片零基帧号；从这里到总帧数为最后稳定区间，至少1秒 |
| `assets` | 输入资产列表，格式见下文 |
| `creative` | 全片创作与事实文本 |
| `layouts` | 共享空间与其布局图、对象、布局相机 |
| `shots` | 完整连续镜头时间线 |
| `provider` | 实际平台信息；未核实时保持`unverified` |

`creative`的必需字段为`concept`、`product_facts`、`unknowns`、`look`、`lighting`、`material_process`、`identity`、`text_lock`、`photography`。除了可以为空的`unknowns`，必需字段应为非空文本；无料体时明确说明本次不设计料体过程，不编造内容填字段。可选`scene_design`、`visibility`、`previs_rules`分别填写置景结构、文字可见度和预演职责；正常业务建议完整撰写这些文本，避免依赖通用回退句。完成正文需要的完整句子放这里，不能只填标签词。

资产结构：

```json
{"id":"LAYOUT_A_IMAGE","role":"layout","path":"inputs/layout-a.png","sha256":"填写实际文件的64位SHA256"}
```

`role`为`product`、`look`、`layout`或`art`。真实业务契约必须具备产品、影调和布局三类输入；fixture可只有明确标注技术fixture的布局图。角色和哈希只检验文件关联，不能证明看过图、图由AI生成或美术质量合格；真实生成输入、工具返回与查看记录另存证据。

### 布局、对象与布局相机

每个布局为`{id,image_asset,rationale,objects,camera}`。`image_asset`必须指向一个`role=layout`的资产，即使fixture也不能没有图。`rationale`写当前产品依据与该空间的镜头作用，不写泛泛“高级场景”。

对象字段：

```json
{
  "id":"PRODUCT_PROXY","role":"product","primitive":"cube",
  "location":[0,0,1],"dimensions":[1,0.6,2],"rotation_deg":[0,0,0],
  "color":[0.8,0.8,0.8],"rationale":"以基本体记录产品占位与主姿态"
}
```

`role`为`product`、`set`或`material`；`primitive`为`cube`、`sphere`、`cylinder`、`plane`或`mesh`。位置、尺寸用一致的场景单位，旋转为角度，颜色分量为0—1。尺寸必须为正；`plane`仍给薄的正Z尺寸用于边界判断，实际渲染为平面。同布局内对象ID唯一，每套布局至少有一个产品代理。初始版本不导入客户精细模型，不运行流体求解器。

`primitive=mesh`时在同一个对象中增加`vertices`与`faces`：顶点是至少3个有限三维坐标，面是至少1个由3个以上不同顶点索引组成的列表，索引从0开始。顶点至少跨越两个轴，可以是开放平面；当前低成本实现上限为5000顶点、10000面。其他primitive不接受这两个字段。

mesh的顶点描述形状，后端先按原始包围盒中心归中，再逐轴规范化到单位跨度，最后按`dimensions`缩放、按`rotation_deg`旋转、按`location`放置。因此`location`指包围盒中心，`dimensions`给最终轴向尺寸，不能同时把顶点当世界坐标再次加同一偏移。某轴没有跨度时该轴保持0，正的dimensions不自动给平面增加厚度。弧面或折面装置要以这些规则保持关键形状，必要厚度由顶点/面实际建立。

布局相机只需一个`frame=0`的关键点。相机定义`{sensor_width_mm,keys}`，可选`interpolation`和`endpoint_mode`，每个键为：

```json
{"frame":0,"position":[3,-5,2.4],"target":[0,0,1],"lens_mm":55,"roll_deg":0,"ease":"smoothstep"}
```

也可用`fit`替代`position`，仍明确`target`：

```json
{"frame":0,"fit":{"object":"PRODUCT_PROXY","height_fraction":0.62,"azimuth_deg":-55,"elevation_deg":12,"target_offset":[0,0,0]},"target":[0,0,1],"lens_mm":55,"roll_deg":0,"ease":"smoothstep"}
```

`fit`根据真实代理边界投影求距离，避免对所有产品使用固定distance。比例、角度、焦段只是这个构图示例，不是推荐默认值。投影检查不能代替真实布局图对照、产品字形或标签可读性判断。

### 镜头、动画与构图检查

每镜包含`id`、`layout`、`start`、`end`、`purpose`、`entry_state`、`exit_state`、`transition`、`camera`、`animations`、`framing`和`narrative`。

- `start`/`end`是全片零基帧区间`[start,end)`，首尾必须连续、无空隙或重叠，完整覆盖`[0,duration_frames)`。
- 单镜本地键从0到`end-start-1`，起止键均须存在、按帧递增。静态对象保持布局中的姿态，不需要伪造运动。
- `transition`为`{kind:"hard_cut",relation,description}`；`relation`为`continuation`、`association`或`display_time`。初始脚本实际合成硬切，不能在文字中冒称已完成叠化/速度转场。末镜也保留结束关系说明。
- `narrative`为`{camera,subject,light,material,cut}`，各字段写有内容的自然语言，供完整正文使用。它描述创作，不证明对应光影/料体已经被引擎执行。

对象动画为`{object,keys}`，可选`interpolation`和`endpoint_mode`；每个键包含`frame`、`location`、`rotation_deg`、`scale`和`ease`。位置/旋转给完整值；`scale`是布局基础尺寸的乘数。多圈旋转按连续角度显式编码，不能期待脚本自动选择短路或绕一圈。初始版只执行代理变换，复杂料体形变或真实部件需在能力范围内另行落实并更新证据。

相机和对象的`interpolation`默认`hermite`，按真实帧时间计算中心切线，内点保持C1连续，支持非共线多点路径；不是每到一个途经点就停下。其`endpoint_mode`默认`continue`，端点使用单边割线斜率，允许硬切时保留动势；明确需要停车时设为`stop`，端点导数归零。相邻重复频道段的切线仍为零以维持停留。显式`segment`模式按左键`ease`逐段插值，`ease`支持`linear`、`smoothstep`和`smootherstep`。按剪辑需要选择，不把全体镜尾都停下写成审美要求。

后台将相机位置、朝向、焦段和对象变换按半帧烘焙，保存的F-curve使用LINEAR，避免额外BEZIER脉冲改变声明曲线。朝向使用目标与稳健上方向处理；靠近极点、大幅转向仍必须通过实际读回与播放检查。

最后稳定段必须完全位于末镜内，不能再有切镜。相机和所有动画代理在该段前后重复完整相同状态，契约会拒绝仍继续的主运动；初始后端不靠仅声明`hold_start`制造稳定证据。最终材质的微小余动属于单独外观设计，不能冒充白模执行结果。

`framing`包含：

```json
{"object":"PRODUCT_PROXY","min_height":0.2,"max_height":0.9,"safe_margin":0.04,"require_full":true,"min_visible_fraction":0.8}
```

这些数字仅展示格式。逐镜按目的设置可用占比与安全范围；特写允许`max_height>1`并设置`require_full=false`以保留有意裁切。脚本逐帧检查归一化代理包围盒、采样射线可见比例和相机碰撞；它不读产品文字，也不能穷尽所有遮挡或细微穿插。

### 平台信息

`provider`记录`status`、`name`、`entry`、`checked_at`、`evidence`、`max_seconds`、`max_images`、`supports_video_reference`和`label_syntax`。未知能力不能用猜测值伪装成`verified`。仅有`verified`字段声明也不证明实际账户或视频生成成功；必须有对应入口和用途的证据。编译器不上传，不发起最终视频任务。

## 3. 运行顺序

先阅读当前脚本`--help`，确认环境实际参数。按布局静帧 → 实际对照 → 全片动画 → 合成/冷打开 → 原速查看 → 编译执行，不能并发覆盖同一lane。布局对照由代理完成，不自动增加用户审批节点；用户明确的审阅节点仍须保留。

### 3.1 先只渲染布局

```text
python scripts/runtime.py validate /business/project/scene.json
python scripts/runtime.py prepare /business/project/scene.json --mode layout --out /business/project/lanes/layout-a --lane layout-a
```

`prepare`只准备新lane和派发数据，不启动桌面或浏览器。它校验资产/时间/引用并复制到lane内，将`core.py`和`blender_worker.py`复制到`code/`冻结执行代码。读取输出的`mcp-layout.json`，以其中`tool`及`arguments`调用当前真实MCP，沿用已绑定路径与哈希，不手写另一套输入。`layout`后台只建立布局场景，写出`layouts/<布局ID>.png`、`layout-report.json`和`layout-preview.blend`，不会构建逐镜动画或输出整片视频。

lane必须是未存在的新目录。契约或worker修改后使用新版本lane，不编辑旧lane的`scene.json`、`code/`再沿用旧报告；其后检查会拒绝变化。已生成的媒体、审阅和delivery也不覆盖。

后台工作由`blender_worker.py`的`run(job_path)`承担。作业`schema`为`product-tvc-job/v1`，记录规范化契约哈希、绝对`contract_path`、`lane_root`和`mode`。`layout`只渲静态布局；`build`从独立干净后台进程搭建、渲染全片与保存；`inspect`冷打开保存的动画blend读回，不重建或重渲染。

当前已测试的`execute_blender_code_for_cli`入口支持将`--factory-startup`作为启动值，用于没有用户blend的干净建场；这不是所有Blender MCP的通用接口。应读取`prepare`给出的当前派发数据并核实本机入口，不能声称空`blend_file`一定可用，也不依赖旧客户blend作启动资产。

长作业使用派发代码经`bpy.app.binary_path`启动独立隐藏后台worker，lane内记录PID、日志与结果；短MCP调用返回不等于渲染完成。以`status`读取派发记录、日志尾部与产物存在状态，同时核实操作系统中的PID及输出增长；`status`本身不证明进程仍存活或工作成功。原作业未结束时不能针对同一目标再次启动。派发文件以独占方式创建以拒绝重复作业；真实失败时先确认无仍在写的进程，修正后使用新lane。无后台入口时报告缺口，不擅自切换到桌面。

```text
python scripts/runtime.py status /business/project/lanes/layout-a
```

实际并看每张AI布局图和对应预览，修正后保存业务目录中的`layout-review.json`，其格式为：

| 字段 | 内容 |
| --- | --- |
| `schema` | `product-tvc-layout-review/v1` |
| `source_contract_sha256` | 当前源契约的规范化JSON哈希，取`validate`输出的`sha256`或预览lane的`source_contract_sha256`，不是原JSON文件的字节哈希 |
| `preview_lane` | 实际布局预览lane的绝对路径 |
| `layout_report_sha256` | 当前`layout-report.json`文件的SHA256 |
| `reviewer`、`method` | 执行查看的代理/审阅者及实际对照方式 |
| `layouts` | 每个源布局一项，含`id`、`source_image_sha256`、`preview_image_sha256`、`status`与`observations` |

每项`source_image_sha256`对应契约布局源图，`preview_image_sha256`对应本次真实渲染；`observations`说明占比、遮挡、层次、负空间和仍有差异。只有实际对照满足当前设计时填`status=pass`。软件检查记录、版本与结果声明，不证明人或代理实际看过图。发现问题先更新源契约/图并建立新预览lane；旧对照不能继续用。

### 3.2 再建立全片动画

```text
python scripts/runtime.py prepare /business/project/scene.json --mode build --layout-review /business/project/layout-review.json --out /business/project/lanes/lane-a --lane lane-a
```

真实业务的build必须有上述哈希绑定布局对照；缺失、版本变化或任一布局未通过都会被拒绝。读取新lane的`mcp-build.json`并派发，后台完成逐镜动画渲染。`layout-review-before-build.json`保存实际使用的前置对照。技术fixture允许为狭窄测试单独build，但完整流程测试仍应覆盖布局预览/对照这一步，不把此开发例外用于真实业务。

以`status`检查这个动画lane，渲染结束且报告没有问题后：

```text
python scripts/runtime.py assemble /business/project/lanes/lane-a --ffmpeg /tools/ffmpeg --ffprobe /tools/ffprobe
python scripts/runtime.py reopen-request /business/project/lanes/lane-a
```

这里的可执行文件路径仅为示例。`reopen-request`生成`mcp-inspect.json`，再次经其指定后台MCP派发新的worker，冷打开本lane的`scene.blend`，等到`reopen.json`生成并完成后再运行：

```text
python scripts/runtime.py inspect /business/project/lanes/lane-a
```

`inspect`命令校验报告与媒体，不能替代Blender冷打开。非空后台问题列表、缺帧、版本不一致或媒体时间不符必须修复，不能靠忽略日志继续发布。`inspect`返回的`binding`是完整产物哈希集合，必须原样用于该版本的实际审阅记录。

### 3.3 原速审阅与编译

实际查看AI布局、对应渲染与完整原速预演后，将真实审阅记录写入业务文件：

```text
python scripts/runtime.py review /business/project/lanes/lane-a --review /business/project/review.json
python scripts/runtime.py compile /business/project/lanes/lane-a
```

审阅文件需包含`binding`以及非空`reviewer`、`method`、`layout_comparison`、`motion_observations`、`remaining_issues`和`narrative_reconciliation`；最后一项说明逐镜设计文字与实际轨迹/播放结果的语义对照。记录`playback_complete=true`、`playback_speed=1`和`status`（`pass`或`needs_revision`）。`binding`原样取当前`inspect`输出。填写实际观察内容和时间范围，不能只写“已检查/无问题”。若`independent=true`，还需可定位的`sealed_first_review`记录；作者自检应如实为非独立。

还需`layouts`列表，覆盖每个实际布局，逐项包含`id`、当前布局源图的`image_sha256`和具体`observations`。真实业务每项另含`generation:{tool,input_record,output_record}`，记录实际图像工具、生成输入证据与返回输出证据的可定位位置；fixture明确按技术示意对照，不填虚构生成来源。文字声明与哈希是可追溯证据，脚本不能独自证明工具确实生成图像或审阅者真的看过。

只有实际完整原速观看后才能填写完成字段，无法播放时不强填`true`，在业务报告列缺口。默认编译需要与当前binding一致且状态为`pass`的审阅；`compile --allow-unreviewed`仍要求全部技术产物校验，只生成明确标注未审阅的草稿。它可用于调试或用户允许的阶段交付，不能将绕过审阅的稿称为已完成预演验证。软件可以验证字段与版本，不能证明人或代理实际观看过。

需要字符限制时使用`compile`的`--limit`与`--reserve`，数值取本次用户/入口真实要求。全部成功仍只证明当前阶段，最终视频和用户验收各有独立证据。

## 4. 正文和平台映射定稿

已冻结的媒体不需要因删重复句、调整正文长度或形成真实平台附件映射而重渲染。先把每个最终单元的完整正文存为业务目录中的UTF-8文件，再写定稿manifest并执行：

```text
python scripts/runtime.py finalize /business/project/lanes/lane-a --edits /business/project/final-text/manifest.json
```

manifest的`schema`为`product-tvc-final-text/v1`，其`binding`原样取当前`inspect`输出。`semantic_review`为非空审读说明，指出正文与实际路径、主信息、产品状态、切点和时间的对照结果；`provider`可省略以继承契约，或填有实际证据的最新入口信息。

`units`为至少一个单元的列表，每个单元包含：

| 字段 | 内容 |
| --- | --- |
| `id` | 唯一安全标识，用于输出文件名 |
| `start`、`end` | 全片零基整数帧区间`[start,end)`，单元首尾连续并完整覆盖实际全片 |
| `shot_ids` | 该区间与实际镜头相交的镜号，保持实际顺序；不把镜头数等同生成任务数 |
| `prompt_path` | 相对manifest父目录的真实正文文件，不得越界；正文完整且无未填占位符 |
| `entry_state`、`exit_state` | 该单元独立的进入与退出状态说明 |
| `limit`、`reserve`、`count_unit` | 字符上限可为`null`，余量为非负整数；计数单位为`codepoints`、`utf16`或`both`，默认`both` |
| `attachments` | 本单元实际映射，逐项`{id,sha256,purpose,upload,platform_label}` |

附件ID可引用契约中的原素材、`PREVIS-<镜号>`或`PREVIS-FULL`，哈希必须与当前lane匹配。每份附件的`purpose`说明它拥有的属性和使用范围；`upload`是拟议使用标志，不代表执行上传。用户/入口未核实情况下，所有映射保持`upload=false`、`platform_label=null`，交付中性角色表。

正文中的显式编号与该单元的`attachments`必须双向一致：每个引用都要有映射，每个映射都要在本单元正文中明示。原素材ID、`PREVIS-*`按完整ASCII编号匹配，已核实的`platform_label`可作为对应ID的别名；不把镜号标题当成附件。使用整片预演时，正文C栏须改为`PREVIS-FULL`，不能仍列逐镜编号。布局图若在D栏保留编号，就要映射；若只作作者分析资料，应改写成不声称提供该附件的空间设计说明。各单元独立检查，不能借另一单元的附件补齐。

`PREVIS-`是生成视频附件的保留前缀，原素材不能使用；镜号不得为`FULL`。脚本还拒绝未映射的常见`@图片1`、`@视频1`、`@音频1`（或对应英文）标签。检查范围是明确编号与已声明别名，不猜测任意自然语言、未知平台的其他标签语法或附件语义是否充分。`delivery.json`中每单元的`prompt_attachment_ids`保存实际匹配的中性ID，便于人工复核。

只有`provider.status=verified`且有实际入口证据时，才填拟议上传标志和该单元内唯一的真实标签；核实单元时长、图片数量和视频参考能力。脚本根据提供的能力字段检查限制，不能独自证明外部证据真实性、标签语法被入口接受或附件集合足以维持产品身份。代理仍须保留本单元唯一文字/结构权威，不能默默遗漏。

`platform_label`仅用于`upload=true`的映射，且不得与任何中性附件ID重名；其他映射保持`null`。定稿单元ID在大小写不敏感文件系统中也必须唯一。

`finalize`重新读取真实正文、计算Unicode/UTF-16长度和文件哈希，检查manifest时间覆盖、镜号、资产绑定与申报平台限制，再写`finalized-delivery/<单元ID>.md`和`delivery.json`。它检查manifest的时间算术，不从全文自动证明每句时间、运动和状态正确；正文语义由前述审读负责。

交付记录的`finalizer_package_files`保存本次定稿所用包的逐文件哈希；原lane仍保留实际渲染时的脚本版本。纯文字或映射修订可使用新版定稿器，不能据此改称旧媒体由新版渲染器产生。

已有输出拒绝覆盖。再次定稿使用`--out`指定本lane内新的目录，例如`/business/project/lanes/lane-a/finalized-v2`，既有媒体保持不变。命令允许记录尚未完成播放审阅的文本版本，但其状态是`finalized_text_pending_playback`，不得交付为视觉检查完成。正常已审版本可标为`finalized_text`，仍不代表最终视频生成或用户验收。

若正文修订要求实际镜头、动作、几何、时长或切点改变，则修订业务契约并创建新lane，不通过finalize改写旧媒体事实。每个最终单元须能独立复制和使用，不能只存局部改句或“沿用上段”。

## 5. 技术fixture与离线测试

```text
python scripts/runtime.py fixture --out /business/tests/fixture-a
python scripts/runtime.py validate /business/tests/fixture-a/fixture.json
python scripts/test_runtime.py
```

fixture创建15秒、9镜、2套共享布局、12fps、180×320的低成本技术案例及其合成布局示意；末尾16帧为停留。此配置只用于测试，不能升级成业务默认帧率/分辨率、AI美术样片或最终生成效果。目标已有fixture时拒绝覆盖，应换新目录。

用fixture验证合法契约可运行，以及非法时间、引用、路径、哈希等被拒绝。后台完整流程测试按同一layout/对照/build/assemble/inspect链路执行；狭窄worker测试可使用fixture例外。脚本测试通过不能替代真Blender运行。维护阶段可检查本包独立运行，但正常业务调用不要求运行仓库总路由或其他Skill的测试。

## 6. lane产物与解释边界

| 产物 | 用途 |
| --- | --- |
| `scene.json`与`inputs/` | 本lane复制的只读输入及规范化契约 |
| `lane.json`、`job.json`、`code/` | lane资源、输入/包哈希、冻结worker代码与建场作业 |
| `mcp-layout.json`、`mcp-build.json`、`mcp-inspect.json` | 各阶段lane中对应的后台MCP派发入口 |
| `layout-dispatch.json`、`build-dispatch.json`、`inspect-dispatch.json`及对应console日志 | 对应阶段的实际命令、PID、启动时间与执行输出 |
| `layout-preview.blend`、`layout-report.json` | 布局预览lane的静态场景和布局渲染报告，不含逐镜动画 |
| `layout-review-before-build.json` | 动画lane绑定的前置布局对照记录 |
| `scene.blend` | 保存的实际代理场景与烘焙动画 |
| `layouts/<布局ID>.png` | 从布局机位渲染的对照图 |
| `shots/<镜号>/%06d.png` | 本地1起始帧编号的逐镜帧序列 |
| `backend-report.json` | 引擎、版本、进程、实际帧/半帧采样、构图/碰撞问题 |
| `reopen.json` | 冷打开读回及与建场证据的比较 |
| `media/<镜号>.mp4`、`media/previs.mp4`、`media-report.json` | 实际逐镜/完整预演、帧数、时长、解码与哈希 |
| `visual-review.json` | 明确版本上的实际观察记录 |
| `delivery/prompt.md`、`attachments.json`、`measured-shot-summary.json`、`delivery.json` | 完整正文、中性素材库存、实测镜头摘要与交付状态；后3项也在`delivery/` |
| `finalized-delivery/<单元ID>.md`与`delivery.json` | 冻结媒体之上的最终正文、实际附件映射、字符数和哈希；也可使用`--out`给出的新版本目录 |

初始后台使用Workbench验证代理几何和运动，不能据此证明最终材质、光影或流体。后台报告只在渲染完成后写出；`issues`非空须处理。全帧加半帧采样提高运动检查密度，但仍不是连续时间的数学证明；包围盒、射线和碰撞采样也不是品牌可读性或最终像素质量证明。

交付实际文件与哈希，不用“成功退出”代替布局质量、原速播放或用户验收。发现问题时先定位输入、设计、执行、媒体还是审阅缺口，只重做受影响链路；已完成与未验证项如实分开。
