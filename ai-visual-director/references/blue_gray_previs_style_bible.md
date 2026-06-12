# 01_blue_gray_previs_style_bible.md

Source reference: `Storyboard 模版/HKNgc2taYAAehkG.jpeg`, left column only.

This file is the style bible for the Custom GPT: **蓝灰预演草图师 / Blue-Gray Previs Sketcher**.

The right column of the reference sheet is not a style source. Do not absorb its photoreal skin, real lighting, lens polish, photographic city texture, or live-action finish. The target is the left-column production sketch grammar only.

---

## 1. Purpose

本文件用于「蓝灰预演草图师 / Blue-Gray Previs Sketcher」，目标是锁定参考图左列的 **blue-gray previs sketch** 风格，使 GPT 在根据 shot specs、shot list、参考图或 photoreal frame 生成图像时保持稳定一致的导演预演草图语言。

它的用途不是教人画传统 storyboard，而是为 AI 图像生成提供可复用、可约束、可诊断的风格规则：

- 固定目标风格：rough production storyboard sketch / animatic previs sketch / director's working storyboard thumbnail。
- 保留镜头设计：机位、景别、构图、尺度关系、前中后景必须可读。
- 限制完成度：必须像工作草图，而不是 final art。
- 防止风格漂移：避免变成漫画、anime、manga、写实素描、精修插画、丰富水彩、概念设计稿或 photoreal cinematic frame。
- 将 photoreal reference 转译为 sketch grammar：只继承 shot design、pose、scale、blocking、location logic，不继承真实摄影质感。

核心判断标准：**这张图是否像导演和摄影指导在预演镜头时会快速画出的工作图，而不是给观众欣赏的成品插画。**

---

## 2. Style Definition

目标风格是：

> A rough production storyboard frame rendered as an animatic previs sketch: loose black pencil linework over a clean white paper background, with very light blue-gray storyboard wash and sparse tonal blocks used only to clarify space, scale, and atmosphere. Characters are simplified, often faceless, sometimes with visible construction lines. Environments are cinematic but sparse, using minimal perspective cues, blocky architecture, small shorthand pedestrians, and simplified props to preserve camera readability without becoming polished illustration.

精确定义：

- 它是 **rough production storyboard frame**，不是插画完成稿。
- 它是 **animatic previs sketch**，用于预演镜头、blocking、scale、camera logic。
- 它是 **director's working storyboard thumbnail**，允许粗糙、搜索线、未完成边缘。
- 线稿应为 **loose black pencil linework** 或 dark graphite sketch line，保留手绘不确定性。
- 色调应为 **very light blue-gray storyboard wash**，作为空间块面和空气感，不作为绘画主角。
- 明暗处理应为 **sparse tonal blocks**，稀疏、低密度、服务可读性。
- 背景应为 **clean white paper background**，大量留白，不填满画面。
- 人物应为 **simplified faceless character**，无真实五官、无皮肤质感。
- 可以出现 **visible construction lines**，尤其是头部十字线、姿态轴线、透视辅助线。
- 环境应为 **sparse cinematic environment detail**，足够表达地点和空间关系，但不精修建筑、街景或材质。

这是一种“低完成度但高镜头信息密度”的视觉语言：粗糙不是缺陷，而是生产属性；简化不是偷懒，而是为了让镜头逻辑优先于表面美感。

---

## 3. Style Fingerprint

| Attribute | Target | Avoid |
| --------- | ------ | ----- |
| line quality | 松散、粗糙、手绘、略颤动的 searching lines；线条像在寻找轮廓，而不是一次性精确落笔 | 平滑闭合线、clean vector line、漫画勾线、精修插画轮廓 |
| line weight | 黑色或深石墨线；主轮廓略重，内部结构线和远景线更轻；粗细变化自然但不装饰化 | 统一机械线宽、过度书法化线条、厚重漫画外轮廓 |
| construction lines | 允许并鼓励保留头部十字线、姿态轴线、透视搜索线、修正线 | 删除所有草图痕迹，使画面过于干净或像成品插画 |
| face treatment | 无五官或近乎无五官；可用十字辅助线表达头部方向 | 详细眼睛、睫毛、嘴唇、鼻梁、表情肌、真实皮肤 |
| body treatment | 比例写意但动作清楚；肩、臂、手势、躯干方向服务 pose 和 blocking | 精准人体解剖展示、fashion pose、美型人体、肌肉或皮肤渲染 |
| hand / foot treatment | 手脚简化为可读形状；关键动作必须清楚；巨足需简化但解剖方向可读 | 过度细化指甲、皮纹、鞋面材质；或简化到动作无法判断 |
| wash color | 极淡、低饱和 blue-gray；偏冷、偏空气感，可略带灰蓝水痕 | 高饱和蓝、彩色调色、暖色电影调光、真实环境色 |
| tonal density | 稀疏块面；少量浅灰蓝和淡灰用于空间分层、天空、建筑侧面、阴影提示 | 全画面铺满色彩、复杂明暗、完整水彩、厚涂、真实光照 |
| paper background | 干净白纸，大量留白；画面像 storyboard thumbnail 放在页面上 | 满版插画背景、纹理纸喧宾夺主、暗背景、电影画幅仿真 |
| environment detail | 城市、建筑、街道、车辆、行人用 shorthand 表达；只保留空间和尺度所需信息 | 过度渲染窗户、招牌、材质、街景细节、真实城市摄影质感 |
| perspective detail | 使用少量竖线、地面线、消失方向、建筑块面证明机位和空间 | 透视混乱、装饰性背景、无地平线逻辑、无尺度参照 |
| composition density | 中低密度；主体、参照物、透视线清晰；留白明显 | 密集插画、信息塞满、每个区域都被画满 |
| finish level | production sketch level：可读、粗糙、未完成、用于决策 | polished illustration、concept art、key visual、poster art |
| emotional tone | 冷静、功能性、观察式；情绪通过 pose、距离和构图传达 | 戏剧化表情、夸张漫画情绪、美少女凝视、海报式煽情 |
| camera readability | 景别、机位高度、视角、前中后景、尺度关系必须一眼可读 | 画得漂亮但看不出是低角度、远景、特写、巨物尺度或地面机位 |

---

## 4. Visual Grammar

### 4.1 Linework

线稿是主导层。所有画面首先应被读成 hand-drawn production storyboard，而不是被读成水彩、漫画或概念图。

Linework rules:

- 使用 loose black pencil linework 或 dark graphite sketch line。
- 线条应 loose、imperfect、slightly rough、not fully closed。
- 允许 searching lines：同一轮廓附近可以有两三条轻微偏移的修正线。
- sketch corrections allowed：手、头、建筑边缘、透视线可以保留修正痕迹。
- 可见的 construction lines 是风格资产，不是错误。
- 远景建筑和小人物可以用更轻、更短、更断裂的线表达。
- 近景主体轮廓可略重，但不能变成 comic contour。
- 线条应服务镜头结构：地面透视线、建筑竖线、主体姿态线比装饰线更重要。

Avoid:

- no clean vector line
- no polished comic contour
- no manga inking
- no decorative cross-hatching
- no hyper-accurate academic sketching
- no finished character design sheet line cleanup

关键原则：**线条可以粗糙，但镜头信息不能粗糙。**

### 4.2 Blue-Gray Wash

蓝灰 wash 是辅助层，不是主画法。

Wash rules:

- extremely light：接近纸面白度，只轻微压低明度。
- low saturation：冷淡、灰蓝、空气感，不鲜艳。
- used as spatial block and atmosphere：用于天空、远楼、墙面、地面阴影、巨大物体背侧、反射面等空间块。
- secondary to linework：wash 永远不能压过线稿。
- sparse tonal blocks：一块一块地放，边缘可松散，不需要完整填色。
- 可以有淡水痕或干刷感，但必须保持 production sketch 的速度感。
- 灰调可以帮助分离 foreground / midground / background，但不要做真实光影。

Avoid:

- not rich watercolor
- not painterly rendering
- not full color illustration
- not cinematic color grading
- not volumetric light painting
- not photoreal shadow modeling

蓝灰 wash 的正确角色：**让空间更清楚，而不是让画面更漂亮。**

### 4.3 Character Simplification

人物处理必须保持 storyboard shorthand。

Character rules:

- faceless or nearly faceless：脸部通常为空白椭圆或简单头形。
- optional cross construction lines：可使用竖向中心线和横向眼线表示头部朝向。
- simple head shape：头部轮廓可不精确，重点是方向和比例。
- simplified costume silhouette：保留服装大轮廓，例如水手服领口、短袖、裙形、袜子、鞋。
- readable props：耳机、鞋、书包、手机、手中物件等剧情道具必须可读，但不精修。
- posture conveys emotion：低头、抬手、俯视、伸手、停顿、迟疑等情绪通过姿态表达。
- 手势要清楚到能读出动作，但不需要真实手部结构。
- 人物可略显空心、未完成，身体内部大面积留白。

Avoid:

- no detailed eyes, eyelashes, lips, skin texture
- no beauty portrait
- no anime face
- no fashion illustration anatomy
- no polished hair rendering
- no realistic fabric folds except broad silhouette cues

人物的目标不是“像真实的人”，而是“作为镜头中的 actor/blocking marker 可被导演读取”。

### 4.4 Environment Simplification

环境必须服务空间关系、尺度关系和镜头方向。

Environment rules:

- buildings as simplified blocks：建筑以竖向块体、边线、矩形窗带提示。
- streets as perspective planes：街道用斜线、地面边缘、斑马线、路缘线建立消失方向。
- pedestrians as small shorthand figures：远处行人用短线、点状头、简单躯干表现。
- vehicles as simplified silhouettes：车辆只需外形、轮廓、方向和比例。
- vending machines, bicycles, poles, signs can remain as simplified silhouettes when they clarify Japanese urban street context.
- only necessary spatial cues：只画让镜头成立的元素。
- 前景可以用更重线条或更大块面；背景用淡蓝灰和断线。
- 建筑窗户可用少量重复短线表示，不要逐窗渲染。
- 招牌可画成空白矩形或模糊块面，不写可读文字。

Avoid:

- no over-rendered architecture
- no real signage text
- no photographic facade detail
- no dense city illustration
- no decorative worldbuilding unrelated to the shot

环境的目标不是“城市设计”，而是“镜头空间证明”。

### 4.5 Camera and Composition

风格不能牺牲镜头设计。AI 最常见的失败是把画面画得更漂亮，却丢失机位、景别、尺度和 blocking。

Camera rules:

- shot size must remain readable：wide、medium、close-up、insert 必须能被辨认。
- camera angle must be clear：低角度、仰拍、俯拍、地面机位不能被中和成普通眼平视角。
- foreground / midground / background must be readable：至少用线重、尺寸、重叠、wash 密度区分。
- scale relationship must be proven visually：巨足、微缩人物、高楼、车辆、行人要作为比例证据。
- composition matters more than beauty：主体位置、视线方向、地面线、负空间、参照物优先。
- 如果镜头是低角度，建筑竖线应向上压迫，人物或巨物应有底部视角。
- 如果镜头是地面机位，地面纹理、斑马线、鞋底或脚边缘应成为空间锚点。
- 如果镜头是远景，小人物必须小，但仍可用头、躯干、腿的 shorthand 读成人。
- 如果镜头是特写，保留线稿简化，不自动增加五官和皮肤细节。

基本规则：**不要为了风格漂亮而丢掉镜头逻辑。**

---

## 5. Positive Prompt Anchors

可复用的 prompt style anchors：

1. rough hand-drawn production storyboard frame
2. animatic previs sketch for film blocking
3. director's working storyboard thumbnail
4. loose black pencil linework
5. dark graphite searching lines
6. visible sketch correction lines
7. visible construction lines on the face and pose
8. simplified faceless character
9. faceless oval head with cross construction guide
10. very light blue-gray storyboard wash
11. pale low-saturation blue-gray tonal blocks
12. sparse wash used only for spatial separation
13. clean white paper background
14. unfinished production sketch finish
15. minimal shading, linework primary
16. sparse cinematic environment detail
17. simplified urban blocks and perspective lines
18. shorthand pedestrians and vehicle silhouettes
19. readable foreground midground background staging
20. camera angle preserved as a storyboard sketch
21. scale relationship proven with small figures and street objects
22. rough previs frame, not final illustration
23. quick director's sketch with cinematic composition
24. low-detail blue-gray storyboard atmosphere
25. practical shot-planning drawing on white paper

Recommended style-lock phrase:

> rough hand-drawn production storyboard frame, animatic previs sketch, director's working storyboard thumbnail, loose black pencil linework, visible construction lines, very light blue-gray storyboard wash, sparse tonal blocks, clean white paper background, simplified faceless character, sparse cinematic environment detail, linework primary, wash secondary

---

## 6. Negative Style Constraints

### Realism Drift

- photorealism
- cinematic live-action still
- realistic skin texture
- realistic hair strands
- photographic lighting
- lens blur
- depth-of-field bokeh
- real city texture
- live-action costume material rendering

### Anime / Manga Drift

- anime
- manga
- manga panel
- anime girl face
- large expressive eyes
- detailed eyelashes
- kawaii styling
- clean manga inking
- screen tone
- chibi proportions unless explicitly requested

### Illustration Polish Drift

- comic book style
- polished illustration
- glossy concept art
- key art
- poster art
- fashion illustration
- clean vector art
- crisp digital line art
- polished character design sheet
- decorative contour lines

### Watercolor Drift

- rich watercolor painting
- saturated blue watercolor
- full watercolor background
- painterly rendering
- layered wet-on-wet color
- expressive color splashes
- complete tonal modeling
- beautiful art print finish

### Detail Overload

- detailed facial features
- over-rendered architecture
- detailed windows and signage
- highly detailed cars
- detailed fabric folds
- shoe leather texture
- skin pores
- fingernails
- dense street clutter
- unnecessary background extras

### Text / Label Contamination

- text inside image
- captions
- labels
- shot numbers
- handwritten notes
- arrows
- callouts
- subtitle text
- readable signage
- UI overlays
- watermark

### Continuity Drift

- changing costume silhouette across frames
- changing hairstyle silhouette
- missing headphones or required props
- inconsistent shoe shape
- changing body scale without story reason
- replacing storyboard shorthand with beauty portrait
- changing camera angle from the requested shot
- losing scale references
- converting single frame into multi-panel sheet

---

## 7. Do / Don't Table

| Do | Don't |
| -- | ----- |
| 让线稿优先，先读到 loose black pencil linework | 不要让 wash、色彩或渲染压过线稿 |
| 使用 very light blue-gray storyboard wash 作为辅助空间块 | 不要画成丰富水彩或完整上色插画 |
| 保持 clean white paper background 和大量留白 | 不要填满整张画面或做暗色电影背景 |
| 让人物简化、无五官或近乎无五官 | 不要画详细眼睛、睫毛、嘴唇、皮肤纹理 |
| 保留可见 construction lines，尤其是头部十字线 | 不要把草图清理成无瑕完成稿 |
| 保持镜头角度清楚，例如低角度、地面机位、仰拍 | 不要把所有镜头自动拉回普通眼平视角 |
| 保持 shot size 可读：wide、medium、close-up、insert | 不要只画漂亮主体而丢失景别 |
| 使用前景 / 中景 / 背景分层表达空间 | 不要让所有元素贴在同一平面 |
| 用行人、车辆、建筑、窗户、手、脚证明尺度 | 不要只在 prompt 中声明巨大或微缩而画面无证据 |
| 让环境细节稀疏，只保留空间线索 | 不要过度细化城市建筑、窗户、材质和招牌 |
| 用少量透视线表达街道和建筑方向 | 不要使用装饰性背景替代透视结构 |
| 保留水手服、耳机、鞋、道具等关键 silhouette | 不要把角色重新设计成无关服装或时装造型 |
| 通过姿态表达情绪，例如低头、抬手、迟疑 | 不要依赖精致表情或美型脸传达情绪 |
| 让远处人物成为 shorthand figures | 不要把背景行人画成细节完整的小肖像 |
| 让车辆和自行车成为简化 silhouette | 不要渲染车漆、反光、轮胎纹理 |
| 允许未完成边缘、断线、修正线 | 不要追求 polished illustration finish |
| 使用冷淡、低饱和、浅灰蓝调 | 不要使用高饱和色彩或电影调色 |
| 生成单帧 storyboard frame 时只输出单帧 | 不要生成多格分镜页，除非明确要求 |
| 画面中不出现文字、标签、shot number、手写注释 | 不要添加 captions、labels、arrows、callouts |
| 把 photoreal reference 转译成 sketch grammar | 不要复制 photoreal 光影、皮肤、摄影质感 |
| 让构图服务镜头预演 | 不要为了好看牺牲 blocking、scale、camera logic |
| 在巨物镜头中保持巨大物体简化但可读 | 不要画成 monster fantasy 或破坏场面，除非明确要求 |
| 在微缩人物镜头中让小人仍有人类动作 | 不要让微缩人物像玩具、贴纸或昆虫 |
| 使用空白招牌形状暗示城市 | 不要写可读文字或真实品牌 |

---

## 8. Shot-Type Style Adaptation

| Shot Type | What to Emphasize | What to Simplify | Common Failure | Correction |
| --------- | ----------------- | ---------------- | -------------- | ---------- |
| wide shot | 空间关系、地面平面、主体在环境中的位置、尺度参照物 | 人物细节、建筑窗户、车辆材质 | 变成城市概念图，主体丢失 | 增强主体 silhouette 和地面透视线，减少建筑细节 |
| medium shot | 上半身 pose、手势、道具、背景透视方向 | 五官、衣褶、真实皮肤 | 变成角色插画或 anime bust | 保持 faceless head，背景只保留镜头空间线索 |
| close-up | 构图裁切、手部动作、关键道具、头部方向 | 面部细节、皮肤、睫毛、头发丝 | AI 自动补完精致脸 | 使用 faceless / nearly faceless / cross construction lines 强锁 |
| low-angle shot | 仰拍透视、建筑竖线、主体从下方压迫画面 | 服装细节、真实反射、天空渲染 | 机位被中和成普通正视 | 强调 low-angle camera, upward perspective lines, ground-up view |
| high-angle shot | 地面图形、人物在地面上的位置、俯视比例 | 脸部、建筑立面细节 | 俯拍不明显 | 增加 visible ground plane, top-down spacing, compressed figures |
| ground-level shot | 地面近景、斑马线、鞋底或脚边缘、低视点 | 上方建筑细节、远景人物细节 | 看起来只是普通街景 | 指定 ground-level camera, horizon low, foreground street markings large |
| giant-scale shot | 巨物与行人、车、路口、建筑的比例证据 | 巨物皮肤、鞋材质、破坏细节 | 只是画了一个大脚但没有尺度 | 放入 pedestrians, crosswalk, cars, building windows as scale markers |
| miniature-person shot | 巨大手/脸/道具与小人的比例，小人的动作姿态 | 小人的五官、服装纹理 | 小人像玩具或装饰 | 用 human-readable stick-like shorthand pose，避免 toy-like styling |
| object / prop insert | 物体轮廓、手与物体关系、构图裁切 | 材质、品牌、文字、反射 | 变成产品广告或写实静物 | 保持 loose pencil, pale wash, no readable labels, production sketch finish |
| urban environment shot | 街道方向、建筑块、杆线、车辆、行人密度 | 招牌文字、窗户细节、真实城市纹理 | 背景过度完成，像 concept art | 降低细节密度，用 blocky buildings and sparse perspective cues |

---

## 9. Scale and Surrealism Rules

左列中的巨足、微缩人物、巨人视角属于尺度镜头，不是默认奇幻怪兽场景。它们的重点是 **scale proof**，不是 spectacle。

Rules:

- scale must be proven, not merely stated：画面中必须有比例证据。
- 使用 pedestrians、cars、crosswalks、buildings、windows、hands、feet 作为参考。
- perspective must stay readable：巨大物体和微缩人物必须处在同一个可理解的空间透视中。
- giant foot must remain simplified but anatomically readable：脚、鞋、袜或腿部可简化为大块形体，但方向、接地点、体积必须明确。
- miniature people must remain small but human-readable：小人可以是 shorthand，但要能看出头、躯干、四肢和动作。
- 巨物不要过度细化皮肤、袜子纤维、鞋面材质；这会把画面推向 photoreal 或 fetish detail，不符合 previs sketch。
- 微缩人物不要画成玩具、贴纸、玩偶、昆虫或 Q 版角色。
- avoid toy-like miniature look：小人的比例应是被尺度关系缩小的人类，而不是玩具设计。
- avoid monster fantasy unless requested：不要自动添加怪兽感、尖牙、爪、破坏姿态或恐怖氛围。
- avoid destruction unless requested：不要自动画倒塌建筑、爆炸、碎裂地面、逃难人群。
- 如果场景需要压迫感，用构图、遮挡、低机位和比例对比表达，而不是增加灾难细节。

Practical scale devices:

- 巨足跨过斑马线：斑马线条宽度证明尺寸。
- 巨人站在街道：行人和车辆贴近脚边证明高度。
- 手指拎起微缩人物：手指体积与小人四肢动作同时可读。
- 巨人脸部靠近城市天际线：头部轮廓、建筑高度、远处 skyline 建立尺度。
- 低角度看巨大人物：地面近景线条放大，建筑竖线向上收束。

Failure test:

> 如果遮住 prompt 文本，观者是否仍能从画面证据看出“巨大”或“微缩”？如果不能，尺度失败。

---

## 10. Character Continuity Rules

多镜头中人物连续性应通过 silhouette 和关键道具保持，而不是通过详细面部。

Rules:

- same costume silhouette：例如水手服领口、短袖、裙形、袜子、鞋的形状要一致。
- same hairstyle silhouette：头发外轮廓、发长、马尾或披发方向保持一致；不要渲染发丝。
- same headphones / shoes / props：耳机、鞋、书包、手机、手中人物或道具是连续性锚点。
- simplified face treatment remains consistent：如果一格是 faceless with cross construction lines，后续也保持相同简化级别。
- same body scale unless scale change is the story：正常连续镜头中人物体量一致；只有故事要求巨大化或微缩时才改变。
- emotion through pose, not face detail：迟疑、震惊、好奇、俯视、伸手、低头通过身体姿态和构图表达。
- 手部动作要连续：上一镜头看手，下一镜头触碰玻璃或拎起小人时，手势逻辑要接得上。
- 服装细节只保留识别锚点，不逐镜增加装饰。

Continuity anchors for the reference character:

- large over-ear headphones
- simplified school uniform silhouette
- short-sleeve sailor-style top
- dark skirt shape when visible
- faceless head or cross-guided head
- slim teenage/student body proportion, simplified
- cautious or observant posture expressed by head tilt and hand position

---

## 11. Environment Continuity Rules

环境连续性不等于细节复制。它是 geography、screen direction、scale references 和简化视觉锚点的连续。

Rules:

- geography：街道方向、路口位置、建筑相对关系要一致。
- screen direction：角色看向、走向、手伸向的方向在连续镜头中不能无故反转。
- weather / time of day：保持同一冷淡白天、浅蓝灰空气感；不要跳到黄昏、夜景或霓虹。
- building density：城市密度保持中高，但用简化块体表达。
- street direction：地面边线、斑马线、道路透视应维持镜头空间逻辑。
- scale references：行人、车辆、路牌、建筑窗带应作为重复比例证据。
- simplified sign shapes without readable text：可保留招牌、自动售货机、路牌的大形状，但不要写可读文字。
- 如果从街道切到低角度建筑镜头，建筑竖线和反射面可以延续，但不要转成 photoreal architecture。
- 如果从城市地面切到天际线，skyline 应保持蓝灰块面和稀疏竖线，而不是完整城市插画。

Environment continuity test:

> 观者应能感到这些镜头发生在同一类城市空间中，但不应被建筑细节吸引到忘记镜头动作。

---

## 12. Reference Image Usage Rules

当用户上传参考图时，先判断参考图的用途，而不是把所有参考图等权混合。

Reference classification:

- style reference：提取 Style Fingerprint，包括 line quality、wash、finish level、paper background、character simplification、environment detail。
- character reference：保留 costume silhouette、hairstyle silhouette、props、body scale；不要自动复制照片皮肤或插画渲染。
- pose reference：保留姿态、手势、重心、头部方向；转译成 simplified storyboard figure。
- camera reference：保留机位、景别、镜头高度、构图、foreground / midground / background。
- location reference：保留空间结构、建筑密度、街道方向、尺度参照；删除真实材质和文字。
- product / prop reference：保留轮廓、比例、使用方式；避免品牌文字和广告质感。
- first-frame reference：保留 continuity anchors、screen direction、scale logic、shot mood；不要把第一帧风格错误扩散到后续。

Rules:

- never merge all references equally：必须分清“风格源”“构图源”“角色源”“场景源”。
- if the image is a style reference, extract Style Fingerprint：只抽象风格属性，不复制具体内容。
- if the image is photoreal, preserve shot design but convert to sketch grammar：继承镜头，不继承真实光影。
- ignore irrelevant surface realism：皮肤、真实头发、镜头模糊、玻璃反射、服装材质、城市纹理通常应丢弃。
- 如果参考图包含文字、logo、招牌，转成不可读的简化块面。
- 如果参考图是右列那类 photoreal cinematic frame，只能作为 camera / pose / scale / location reference，不可作为 style reference。

Priority order when references conflict:

1. User's explicit shot spec
2. Current style bible
3. Camera / composition reference
4. Character continuity reference
5. Location / prop reference
6. Surface realism from reference image, usually discarded

---

## 13. Prompt Template

```text
Create a rough hand-drawn production storyboard frame.

Style: rough hand-drawn production storyboard frame, animatic previs sketch, director's working storyboard thumbnail, loose black pencil linework, visible construction lines, very light blue-gray storyboard wash, sparse tonal blocks, minimal shading, clean white paper background, simplified faceless character, sparse cinematic environment detail, linework primary, wash secondary.

Subject:
[Describe the main character, object, or scale subject. Keep character details as silhouette and props, not facial beauty.]

Action:
[Describe the clear physical action, pose, gesture, or blocking.]

Scene:
[Describe the location using spatial cues, not rich surface detail.]

Camera:
[Shot size, lens feeling if needed, camera height, angle, direction, low/high/ground-level, close/medium/wide.]

Composition:
[Where the subject sits in frame, negative space, dominant lines, visual hierarchy.]

Foreground:
[Nearest readable elements; use for scale or depth.]

Midground:
[Primary subject/action area.]

Background:
[Simplified buildings, pedestrians, vehicles, skyline, interior blocks, or atmospheric wash.]

Scale relationship:
[How scale is visually proven using people, cars, crosswalks, windows, hands, feet, props.]

Continuity:
[Costume silhouette, hairstyle silhouette, headphones/shoes/props, screen direction, environment geography.]

Must preserve:
[List non-negotiable shot details.]

Aspect ratio:
[e.g. 16:9 single frame, 4:3 storyboard thumbnail, vertical frame.]

Avoid:
photorealism, anime, manga, comic book style, polished illustration, glossy concept art, fashion illustration, rich watercolor painting, clean vector art, 3D render, realistic skin texture, detailed facial features, saturated color, over-rendered architecture, cinematic live-action still, text inside image, captions, labels, shot numbers, handwritten notes, readable signage, multi-panel sheet unless requested.
```

---

## 14. Good Prompt Example

### Sketch Prompt

```text
Create a rough hand-drawn production storyboard frame.

Style: rough hand-drawn production storyboard frame, animatic previs sketch, director's working storyboard thumbnail, loose black pencil linework, dark graphite searching lines, visible sketch corrections, visible construction lines, very light blue-gray storyboard wash, sparse tonal blocks, minimal shading, clean white paper background, simplified faceless character, sparse cinematic environment detail, linework primary, wash secondary.

Subject: a Japanese schoolgirl wearing large over-ear headphones and a simple sailor-style school uniform, simplified faceless oval head with a cross construction guide.

Action: she stands in the middle of a narrow Japanese city street, facing camera, head slightly lowered, looking down at her own raised hands as if confused or quietly discovering something.

Scene: a compact Japanese urban street with simplified vending machines, a bicycle, utility poles, vertical street signs without readable text, distant pedestrians, and blocky mid-rise buildings.

Camera: frontal medium shot, slight street-level perspective, eye-level to slightly low camera height, cinematic but rough storyboard framing.

Composition: the girl is centered in the frame; her hands sit in the lower center; street perspective lines recede behind her; buildings and poles frame both sides; large white paper margins remain visible.

Foreground: minimal street edge lines and the girl's simplified hands.

Midground: the girl, her headphones, uniform silhouette, vending machine shapes, bicycle silhouette, utility pole.

Background: pale blue-gray blocks for distant buildings, small shorthand pedestrians, thin vertical lines for poles and signs, sparse wash for sky and street depth.

Scale relationship: normal human scale established by vending machines, bicycle, pedestrians, poles, and street width.

Continuity: large over-ear headphones, simplified school uniform silhouette, faceless head with cross guide, cautious inward posture, blue-gray sketch grammar.

Must preserve: frontal medium shot, street perspective, headphones, raised hands, faceless simplified character, vending machines, bicycle, utility poles, distant pedestrians, sparse Japanese city street cues.

Aspect ratio: 16:9 single storyboard frame.
```

### Negative Prompt

```text
photorealism, cinematic live-action still, anime, manga, comic book style, polished illustration, glossy concept art, rich watercolor painting, clean vector art, 3D render, realistic skin texture, detailed facial features, detailed eyes, eyelashes, lips, detailed hair strands, saturated color, over-rendered architecture, realistic signage, readable text, captions, labels, shot numbers, handwritten notes, dense city detail, fashion illustration, beauty portrait, multi-panel storyboard sheet
```

### Why It Works

- It names the style as a production storyboard frame, not an illustration.
- It locks linework first: loose black pencil, searching lines, visible corrections.
- It locks the wash as very light blue-gray and secondary.
- It preserves the first left-column shot logic: frontal medium shot, centered girl, hands raised, street perspective.
- It keeps the face simplified with a construction cross instead of anime or photoreal detail.
- It identifies the spatial anchors: vending machines, bicycle, poles, distant pedestrians, buildings.
- It states normal scale visually, preventing accidental surreal scale drift.
- It bans text and signage contamination, a common AI failure in city scenes.

---

## 15. Bad Prompt Example

Bad prompt:

```text
Draw a beautiful hand-drawn anime storyboard of a giant schoolgirl in Tokyo with cinematic watercolor style.
```

Why it fails:

- anime drift：直接要求 anime，会触发大眼睛、精致脸、漫画轮廓和角色美型。
- beauty drift：beautiful 会把工作草图推向观赏性插画，削弱 production sketch finish。
- rich watercolor drift：cinematic watercolor style 会增加饱和色、完整铺色、真实光影或漂亮水彩边缘。
- no camera logic：没有指定 shot size、camera height、angle、composition。
- no foreground/midground/background：没有空间分层，AI 容易生成漂亮但扁平的画。
- no scale reference：说 giant schoolgirl 但没有 pedestrians、cars、crosswalks、buildings、windows 等比例证据。
- no production storyboard feeling：没有 loose black pencil linework、visible construction lines、clean white paper background、sparse tonal blocks。
- Tokyo is too broad：容易诱发霓虹、招牌文字、真实街景或旅游明信片式城市细节。

Corrective direction:

> Replace "beautiful anime" with "rough hand-drawn production storyboard frame"; replace "cinematic watercolor" with "very light blue-gray storyboard wash"; specify camera, composition, scale proof, and negative style constraints.

---

## 16. Quality Checklist

Before generation, check:

- Is linework primary?
- Is blue-gray wash secondary?
- Is the wash very light, low saturation, and sparse?
- Is the character simplified?
- Is the face not detailed?
- Are construction lines visible where useful?
- Is the paper background clean?
- Is there enough white space?
- Is camera angle readable?
- Is shot size preserved?
- Is foreground/midground/background clear?
- Is scale proven when needed?
- Are pedestrians, cars, crosswalks, buildings, windows, hands, or feet used as scale references when relevant?
- Is the environment simplified?
- Are buildings reduced to blocks, verticals, and sparse perspective cues?
- Are props readable but not polished?
- Is there any unwanted text?
- Are there captions, labels, shot numbers, handwritten notes, or readable signs?
- Is the image a single frame when a single frame is requested?
- Is it still a production storyboard, not final art?
- Would a director or previs supervisor understand the shot from the sketch alone?

Hard reject if:

- It looks photoreal.
- It looks anime or manga.
- It looks like polished illustration or glossy concept art.
- It has detailed facial features.
- It has rich watercolor rendering.
- It loses the requested camera angle.
- It states scale but does not prove scale visually.
- It contains text inside the image.

---

## 17. Failure Diagnosis and Correction

| Failure | Symptom | Correction |
| ------- | ------- | ---------- |
| too photoreal | Skin, lighting, lens blur, real city texture, photographic shadow | Add: rough hand-drawn production storyboard frame, no photorealism, no realistic skin texture, clean white paper background |
| too anime | Large eyes, cute expression, manga hair, polished character face | Add: simplified faceless character, oval head with cross construction guide, no anime, no manga, no detailed eyes |
| too polished | Clean final contours, perfect anatomy, finished illustration feel | Add: loose black pencil linework, searching lines, visible sketch corrections, unfinished animatic thumbnail |
| too watercolor | Rich blue washes, full-color atmosphere, painterly edges | Add: very light blue-gray storyboard wash, sparse tonal blocks, wash secondary, not rich watercolor |
| too detailed face | Eyes, lips, nose, eyelashes, beauty portrait | Add: faceless or nearly faceless, no detailed facial features, emotion through pose |
| too detailed city | Windows, signs, shopfronts, vehicles, realistic street texture dominate | Add: sparse cinematic environment detail, blocky buildings, simplified signs without readable text |
| no scale reference | Giant or miniature subject is stated but not visually proven | Add: pedestrians, cars, crosswalks, building windows, hands or feet as scale markers |
| wrong camera angle | Requested low angle becomes eye-level, ground shot becomes normal street shot | Add explicit camera: low-angle / ground-level / high-angle; describe horizon, foreground size, perspective lines |
| multi-panel sheet when single frame requested | AI outputs several panels, borders, sequence sheet | Add: single storyboard frame only, no multi-panel sheet, no captions, no shot numbers |
| text appears inside image | Labels, signs, handwritten notes, subtitles, panel numbers | Add: no text inside image, no captions, no labels, no readable signage, no handwritten notes |
| character continuity drift | Headphones disappear, costume changes, hairstyle changes, props mutate | Add continuity anchors: same headphones, same uniform silhouette, same hairstyle silhouette, same props |
| product / prop distortion | Earphones, shoes, phone, bicycle, vending machine become unreadable or over-designed | Add: readable simplified prop silhouette, preserve function and proportion, no brand text, no product-ad rendering |
| wash dominates linework | Blue-gray blocks overpower the sketch | Add: linework primary, wash secondary, minimal shading, high white-paper visibility |
| environment too empty | No spatial cues; subject floats on blank page | Add necessary perspective planes, building blocks, ground lines, small pedestrians or props |
| environment too dense | Composition becomes cluttered and illustration-like | Add sparse detail only, remove unnecessary extras, simplify background into blocky shapes |
| face expression replaces pose | AI uses detailed expression instead of body language | Add: emotion through posture and gesture, faceless head, head tilt and hand position |
| scale becomes monster fantasy | Giant subject becomes destructive creature or horror scene | Add: avoid monster fantasy, avoid destruction unless requested, production storyboard sketch |
| miniature people look like toys | Small people are plastic, doll-like, cute, or chibi | Add: human-readable shorthand figures, not toys, not chibi, not decorative miniatures |
| realistic signage contamination | Japanese signs become readable text or fake letters | Add: blank sign shapes, unreadable simplified signage, no text |
| composition loses subject hierarchy | Background competes with main action | Add: clear subject silhouette, lighter background lines, sparse wash behind subject |

---

## 18. Final Style Lock

Use this style lock directly in GPT instructions or image prompts:

> rough hand-drawn production storyboard frame, loose black pencil linework, very light blue-gray storyboard wash, sparse tonal blocks, minimal shading, clean white paper background, unfinished animatic thumbnail, director's storyboard sketch, simplified faceless character, visible construction lines, sparse cinematic environment detail, linework primary, wash secondary, no polished illustration, no anime, no manga, no photorealism.

Expanded operational lock:

> Create a single rough production storyboard frame for shot planning. Preserve camera angle, shot size, composition, foreground/midground/background separation, and scale references. Use loose dark graphite searching lines with visible construction marks. Add only very light low-saturation blue-gray wash as sparse spatial blocks. Keep the white paper background visible. Simplify characters into faceless readable figures with consistent costume and prop silhouettes. Simplify environments into blocky cinematic cues, perspective lines, shorthand pedestrians, vehicles, and props. Avoid photorealism, anime, manga, comic polish, rich watercolor, glossy concept art, realistic skin, detailed facial features, over-rendered architecture, readable text, captions, labels, shot numbers, and handwritten notes.
