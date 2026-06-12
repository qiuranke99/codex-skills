# 02_good_shotlist_examples.md

Knowledge file for `Storyboard Shot Planner`.

This file gives reusable examples of good shot-list logic and clean handoff specs. The examples are original composites. They are patterns, not rules. User requirements, exact shot count, output mode, and reference-image priorities always override these examples.

All examples use stable handoff language. They avoid temporary tool-role labels, generator-specific syntax, model names, sampler settings, seeds, CFG, LoRA, ControlNet, and full image-generation prompts.

Use these examples to learn:

- one clear visual job per shot;
- director beat before camera decoration;
- POV and information release;
- cut logic between shots;
- blocking and body pose;
- axis, screen direction, and eyeline;
- foreground/midground/background readability;
- scale and continuity proof;
- clean handoff fields that can be copied directly.

---

## Example 1: 四镜超现实街道尺度揭示

Use case: 单一超现实视觉瞬间，重点是尺度证明、角色脆弱感和非破坏性调度。

### Input Brief

雨后的东京十字路口，一个穿校服的少女放学后走进人群。她突然发现城市像缩小了一样，自己变得巨大。她不是怪兽，而是困惑、小心、害怕伤到别人。需要 4 个镜头。

### Creative Constraints

- 少女必须保持人类感、困惑、谨慎，不要怪兽化。
- 保持雨天街道、湿地反光、出租车、行人、斑马线、店招。
- 保持她从左向右移动，除非用高角度重置空间。
- 尺度必须通过出租车、行人、建筑窗、路灯证明。
- 不要毁楼、踩车、灾难大片感。

### Shot List Table

| Shot ID | Director Beat | Shot Purpose | Shot Size | Camera Angle | Lens Feel | Camera Movement | Action / Blocking | Composition / Depth | POV / Axis / Cut Logic | Scale / Continuity |
|---|---|---|---|---|---|---|---|---|---|---|
| SH_001 | 正常基线 | 建立城市正常尺度与角色身份 | Wide shot | 街角 eye-level | 35mm natural street feel | locked-off | 少女从左向右走入斑马线，身边是正常行人与出租车 | 前景雨伞边缘，中景少女和行人，背景店招与车流 | 客观视点；街道轴线左→右；opening baseline | 正常身高；海军校服、红领结、短黑发、湿皮鞋锁定 |
| SH_002 | 主观发现 | 让观众跟随她发现下方异常 | Medium close-up / OTS | 从她肩后略高角度向下 | mild wide, street drops away | tilt-down reveal | 她停住低头，手悬在胸口，视线落向脚边 | 肩膀和红领结在前景，下方车流变小 | 角色对齐；eyeline 向下；cut from baseline to discovery | 出租车高度低于她膝部；同一雨天与方向 |
| SH_003 | 尺度证据 | 用身体动作证明巨大尺度 | Full wide / scale proof | 出租车保险杠附近低机位仰拍 | 24mm wide with vertical exaggeration | static | 她一只脚悬在出租车上方，双臂张开保持平衡 | 前景出租车和斑马线，中景巨大的鞋与腿，背景高楼夹住身体 | 从发现切到 proof；保持左→右动作向量 | 一只鞋约等于一辆出租车；行人像拇指大小 |
| SH_004 | 情绪后果 | 巨大但脆弱，小心缩在城市中 | Extreme wide | 屋顶高角度俯看 | compressed city-grid feel | slow pullback | 她蹲在楼间，一手轻撑屋顶，不敢碰街道 | 前景屋顶栏杆，中景少女与楼群，背景连续街区和车灯 | 高角度 geography reset；后果镜头 | 手掌覆盖半个屋顶；膝盖高过路灯；无建筑损坏 |

### Clean Handoff Specs

```yaml
SH_001
aspect_ratio: unspecified
scene: rainy Tokyo crossing after school, normal-scale baseline
duration: optional
dramatic_beat: viewer first sees the girl as a normal pedestrian in a normal city
shot_purpose: establish geography, normal scale, character identity, and left-to-right street direction
shot_size: wide shot
camera_angle: eye-level from street corner
lens_feel: 35mm natural street feel, moderate depth
camera_movement: locked-off
cut_logic: opening baseline
panel_moment: decisive frame: girl stepping into crosswalk among normal pedestrians
pov_alignment: objective observer
axis_of_action: street movement axis runs left-to-right across frame
screen_direction: girl moves left-to-right
main_subject: teenage girl in navy Japanese school uniform with red ribbon
main_action: she steps into the rainy crosswalk with normal pedestrians and taxis around her
blocking: girl enters from left third, walking with crowd, school bag at right hip
body_pose: shoulders slightly hunched under rain, one foot forward, gaze ahead
eyeline: forward along crossing direction
composition: girl on left third; crosswalk diagonals lead toward traffic lights
foreground: blurred umbrella tops and wet curb edge
midground: girl, pedestrians, taxis at normal scale
background: shop signs, glass storefronts, rainy traffic signals
scale_reference: normal human height beside pedestrians and taxi roofline
continuity_lock: navy uniform, red ribbon, short black bob, wet loafers, rainy afternoon, left-to-right movement
must_preserve: normal scale baseline; wet reflections; no surreal scale yet
avoid: giant body, destroyed street, sunny weather, fantasy costume

SH_002
aspect_ratio: unspecified
scene: same crossing, first surreal discovery
duration: optional
dramatic_beat: she notices the city below her has become impossibly small
shot_purpose: shift to character-aligned discovery and reveal first scale anomaly
shot_size: medium close-up over shoulder
camera_angle: slight high angle looking down past her shoulder
lens_feel: mild wide feel, perspective makes street drop away
camera_movement: tilt-down reveal
cut_logic: POV shift from objective baseline to her discovery
panel_moment: end frame: her gaze locked downward at tiny traffic
pov_alignment: character-aligned OTS subjective
axis_of_action: same street axis as SH_001
screen_direction: street still reads left-to-right below her
main_subject: schoolgirl looking down at the suddenly tiny street
main_action: she lowers her gaze toward taxis and umbrellas below her
blocking: she has stopped mid-crossing, torso turned slightly toward traffic, left hand near chest
body_pose: shoulders tense, left hand hovering near chest, head tilted down
eyeline: down-right toward tiny taxis near her shoes
composition: her shoulder and hair frame upper left; tiny traffic fills lower right
foreground: edge of her red ribbon and damp hair strands
midground: her hand and torso
background: tiny taxis, umbrellas, crosswalk stripes far below
scale_reference: taxi roof is smaller than her loafer; umbrella dots below waist height
continuity_lock: same uniform, same rain, same left-to-right street geography
must_preserve: discovery through scale contrast, not horror
avoid: monster face, city destruction, extra giant characters

SH_003
aspect_ratio: unspecified
scene: same crossing, scale proof
duration: optional
dramatic_beat: the surreal scale becomes undeniable through physical risk
shot_purpose: prove giant scale through shoe-to-taxi comparison and careful body action
shot_size: full wide scale proof shot
camera_angle: low street-level angle looking up from near taxi bumper
lens_feel: 24mm wide feel with vertical exaggeration
camera_movement: static
cut_logic: scale proof after subjective discovery
panel_moment: decisive action moment: one foot hovering above taxi row
pov_alignment: objective witness camera from street level
axis_of_action: same crossing axis, camera remains on street side
screen_direction: her body still oriented left-to-right
main_subject: giant schoolgirl frozen mid-step
main_action: one foot hovers carefully above a row of stopped taxis
blocking: she stands over the crosswalk, weight held back, foot suspended rather than landing
body_pose: knees bent, arms out for balance, eyes down, mouth slightly open
eyeline: downward toward taxis and pedestrians
composition: shoe dominates lower foreground; body rises through center; buildings frame both sides
foreground: taxi hood and wet crosswalk stripe
midground: giant shoe, leg, stopped taxis, tiny pedestrians
background: vertical neon shop signs and high windows behind her shoulders
scale_reference: shoe length equals one taxi; pedestrians are thumb-sized near curb
continuity_lock: same red ribbon, navy uniform, wet black loafers, rainy afternoon
must_preserve: careful non-destructive posture; readable shoe-to-taxi scale
avoid: crushing cars, torn clothing, kaiju posture, chaotic explosions

SH_004
aspect_ratio: unspecified
scene: rooftop view of same rainy district, emotional consequence
duration: optional
dramatic_beat: the giant figure feels vulnerable inside a fragile city
shot_purpose: resolve the beat with scale, caution, and emotional consequence
shot_size: extreme wide shot
camera_angle: high rooftop angle looking down into city grid
lens_feel: compressed urban-grid feel
camera_movement: slow pullback
cut_logic: geography reset and emotional consequence after street-level proof
panel_moment: end frame: girl crouched small within the city grid despite giant scale
pov_alignment: omniscient geography reset
axis_of_action: overhead reset; prior left-to-right geography remains legible through street layout
screen_direction: not movement-driven; static crouched posture
main_subject: giant schoolgirl crouched between buildings
main_action: she braces one hand on a rooftop while trying not to touch traffic below
blocking: crouched in available space between buildings, elbows tucked inward, hand resting lightly on roof edge
body_pose: crouched inward, elbows close, gaze down and worried
eyeline: down toward traffic and pedestrians
composition: city blocks form a grid; girl centered, curled into available space
foreground: rooftop railing and rain puddles
midground: girl's hand on roof, knees between streets
background: continuous blocks, tiny headlights, shop signs
scale_reference: her hand covers half a rooftop; knees rise above traffic lights
continuity_lock: same uniform, hair, ribbon, rainy district, no building damage
must_preserve: fragile-city feeling; human vulnerability; clear giant scale
avoid: triumphant superhero pose, collapsed buildings, random landmarks
```

### Why This Works

- It starts with a normal-scale baseline before the surreal reveal.
- It shifts POV only when the character discovers the anomaly.
- It proves scale through taxi, pedestrians, streetlights, rooftop, and buildings.
- It uses the final high angle as a geography reset, not a random cool angle.

### Common Bad Version

```markdown
做四个电影感镜头，一个日本校服少女变成巨人，东京雨夜，很史诗，先近景再大远景，最后很震撼。
```

Why bad:

- No normal baseline.
- No POV strategy.
- No scale proof.
- “史诗” pushes toward destruction and monster imagery.
- No axis/screen direction or cut logic.

---

## Example 2: 六镜桌面灯产品广告

Use case: 产品广告，重点是产品身份、功能动作、proof detail、使用场景和 end lock。此例避免医疗/健康/净化等高风险功效暗示。

### Input Brief

为一款可折叠桌面灯设计 6 个镜头广告。产品是 matte white folding desk lamp，copper hinge，warm/cool toggle，USB-C port。广告要表现“凌乱夜间工作 → 产品出现 → 展开 → 灯光切换 → 便携收纳 → 最终产品画面”。

### Shot List Table

| Shot ID | Director Beat | Shot Purpose | Shot Size | Camera Angle | Lens Feel | Camera Movement | Action / Blocking | Composition / Depth | POV / Axis / Cut Logic | Scale / Continuity |
|---|---|---|---|---|---|---|---|---|---|---|
| SH_001 | 问题基线 | 建立暗桌面和工作混乱 | Medium wide | 桌边 eye-level | 35mm natural | locked-off | 设计师眯眼看草图，台灯缺席，屏幕光偏冷 | 前景乱纸，中景人物和桌面，背景夜窗 | 客观；opening problem | 暗桌、手、纸张建立正常比例 |
| SH_002 | 产品出现 | 清楚展示折叠灯身份 | Product close-up | table-height low angle | slight telephoto | slow slide in | 手把折叠灯放到草图旁 | 产品居中，USB-C 口侧面可见 | 从问题切到解决对象 reveal | matte white body, copper hinge, folded state |
| SH_003 | 功能动作 | 展开铰链，证明可折叠 | Medium close-up | over-hand three-quarter | natural macro-leaning | static | 一只手按住底座，另一只手抬起灯臂 | 手和铰链在中景清楚可见 | match on action | 铰链铜色、灯头朝下、无第二个产品 |
| SH_004 | proof detail | 灯光模式可读变化 | Insert / close-up | side angle at toggle | macro feel | locked-off | 拇指拨动 warm/cool toggle，光从冷白变暖白 | toggle 占上三分之一，纸面受光变化在下方 | insert proof | toggle 与手指比例；不要 UI 幻影 |
| SH_005 | 使用结果 | 桌面从混乱变成可工作状态 | Wide overhead | top-down | graphic clean | slow pullback | 灯照亮草图中心，手继续画线 | 产品左上，光区中心，纸张形成层次 | consequence after proof | 灯臂展开状态稳定，铜铰链可见 |
| SH_006 | end lock | 最终产品和便携状态 | Clean packshot | eye-level table angle | slight telephoto | slow push-in | 灯折回半收纳，旁边是充电线和完成草图 | 产品居中，负空间可放标题 | end-frame resolution | matte white, copper hinge, USB-C port readable |

### Clean Handoff Specs

```yaml
SH_001
aspect_ratio: unspecified
scene: late-night design desk, problem setup
duration: optional
dramatic_beat: the workspace is dim and visually strained before the product appears
shot_purpose: establish the lighting problem and normal desk scale
shot_size: medium wide shot
camera_angle: eye-level from desk edge
lens_feel: 35mm natural perspective
camera_movement: locked-off
cut_logic: opening problem baseline
panel_moment: decisive frame: designer squints at sketch under weak screen light
pov_alignment: objective observer
axis_of_action: desk axis runs left-to-right between designer and sketch area
screen_direction: static workspace, hand movement left-to-right across paper
main_subject: tired designer at cluttered desk
main_action: designer leans toward sketch, struggling to see details
blocking: designer sits behind desk, sketch papers spread in front, empty lamp space at left side
body_pose: shoulders forward, one hand on pencil, eyes narrowed toward paper
eyeline: down toward sketch paper
composition: paper clutter foreground; designer midground; dark window background
foreground: sketch sheets, pencil, cold laptop edge
midground: designer's hands and face
background: night window and dim room shelves
scale_reference: normal hand-to-pencil and hand-to-paper scale
continuity_lock: dark desk, sketch papers, designer in gray sweater, no lamp visible yet
must_preserve: dim problem state; product absent
avoid: product appearing early, sunny room, dramatic sci-fi lighting

SH_002
aspect_ratio: unspecified
scene: same desk, product reveal
duration: optional
dramatic_beat: the solution object enters as a clear physical product
shot_purpose: reveal product identity, folded state, material, and orientation
shot_size: product close-up
camera_angle: table-height low angle
lens_feel: slight telephoto compression
camera_movement: slow slide in
cut_logic: reveal after problem baseline
panel_moment: end frame: folded lamp resting beside sketch paper
pov_alignment: product-functional view
axis_of_action: same desk axis; product placed on left side of paper
screen_direction: hand enters from right and exits right
main_subject: matte white folding desk lamp with copper hinge
main_action: hand places the folded lamp beside sketch papers
blocking: product set upright on desk, folded arm facing camera, USB-C port visible on side
body_pose: hand releases product from top, fingers leaving lamp base
eyeline: not applicable
composition: lamp centered; sketch papers lower right; dark laptop edge left
foreground: desk texture and pencil tip
midground: folded lamp, copper hinge, USB-C side port
background: soft blur of designer and night window
scale_reference: lamp base is about the size of a palm; taller than pencil cup when folded
continuity_lock: matte white body, copper hinge, folded state, USB-C port on side
must_preserve: product shape, copper hinge, no logo unless provided
avoid: fake brand text, extra lamp, glossy chrome finish, unrelated device

SH_003
aspect_ratio: unspecified
scene: same desk, unfold action
duration: optional
dramatic_beat: the product becomes functional through a visible hinge action
shot_purpose: prove foldability with hand operation
shot_size: medium close-up
camera_angle: over-hand three-quarter angle
lens_feel: natural macro-leaning
camera_movement: static
cut_logic: match on action from product placement to setup operation
panel_moment: decisive action moment: lamp arm halfway raised at hinge
pov_alignment: product-functional view
axis_of_action: desk axis unchanged
screen_direction: lamp arm opens upward and slightly left-to-right
main_subject: hands unfolding the desk lamp
main_action: one hand holds the base while the other lifts the lamp arm
blocking: lamp base stays planted on left side of sketch paper; hands bracket the hinge
body_pose: thumb and fingers grip copper hinge area; other hand steady on base
eyeline: not applicable
composition: copper hinge on upper third; base lower center; sketch lines visible underneath
foreground: designer's left hand and base edge
midground: copper hinge and rising lamp arm
background: sketch paper and dim desktop
scale_reference: hinge diameter compared to fingertip pads
continuity_lock: same matte white lamp, copper hinge, folded-to-open state, single product
must_preserve: mechanical hinge action; no floating parts
avoid: impossible bending, duplicate lamp, hidden hinge, touchscreen UI

SH_004
aspect_ratio: unspecified
scene: same desk, light mode proof insert
duration: optional
dramatic_beat: the product control produces a visible light-state change
shot_purpose: show warm/cool toggle function through a concrete hand action
shot_size: insert close-up
camera_angle: side angle at toggle switch
lens_feel: macro feel, tactile detail
camera_movement: locked-off
cut_logic: insert proof after unfold action
panel_moment: decisive moment: thumb finishes toggle shift and paper below changes warmth
pov_alignment: product-functional insert
axis_of_action: not applicable
screen_direction: thumb moves right-to-left across toggle
main_subject: warm/cool toggle on desk lamp
main_action: thumb slides toggle, changing cast on paper from cool white to warm white
blocking: lamp head angled down at paper; thumb enters from frame right
body_pose: thumb pad pressing small switch, index finger bracing lamp head
eyeline: not applicable
composition: toggle at upper third; lit paper surface lower half shows color contrast
foreground: thumb and switch ridge
midground: lamp control surface
background: sketch paper with changing light pool
scale_reference: switch is smaller than thumb pad; paper texture shows light coverage
continuity_lock: same lamp, copper hinge nearby, lamp already opened
must_preserve: physical switch and light change, not hologram
avoid: fake UI screen, neon beams, unreadable switch, unsupported technical claims

SH_005
aspect_ratio: unspecified
scene: same desk, productive work result
duration: optional
dramatic_beat: the desk becomes readable and usable after the lamp is activated
shot_purpose: show consequence of the product in the work environment
shot_size: wide overhead shot
camera_angle: top-down over desk
lens_feel: graphic clean overhead
camera_movement: slow pullback
cut_logic: consequence after light-mode proof
panel_moment: end frame: lamp pool of light clearly centered on drawing area
pov_alignment: objective product-use view
axis_of_action: overhead reset; desk geography visible
screen_direction: hand draws left-to-right on paper
main_subject: opened lamp illuminating sketch paper
main_action: designer's hand draws a clean line inside the lamp's light pool
blocking: lamp placed upper left of paper, arm extended diagonally toward center
body_pose: only hand visible, relaxed pencil grip
eyeline: not applicable
composition: lamp upper left, sketch centered, hand lower right, light pool creates visual hierarchy
foreground: none, flat overhead plane
midground: lamp, sketch paper, hand, pencil
background: desk surface, organized tools at edges
scale_reference: lamp arm length compared to A4 sketch paper and hand
continuity_lock: matte white lamp open, copper hinge visible, sketch papers same as SH_001
must_preserve: practical desk-use clarity
avoid: perfect sterile desk, extra products, fake brand text

SH_006
aspect_ratio: unspecified
scene: final clean desk packshot
duration: optional
dramatic_beat: the product resolves as compact, useful, and identifiable
shot_purpose: end lock with product identity, compact form, and completed work context
shot_size: clean product close-up
camera_angle: eye-level table angle
lens_feel: slight telephoto packshot feel
camera_movement: slow push-in
cut_logic: end-frame resolution after use consequence
panel_moment: end frame: lamp centered beside finished sketch and cable
pov_alignment: objective product end lock
axis_of_action: not applicable
screen_direction: static
main_subject: matte white folding desk lamp in half-folded compact position
main_action: lamp rests beside USB-C cable and completed sketch
blocking: lamp centered, copper hinge facing camera, USB-C port visible on side
body_pose: no person visible
eyeline: not applicable
composition: product centered; completed sketch left; coiled cable right; clean negative space above
foreground: desk surface and cable curve
midground: lamp body, copper hinge, USB-C port
background: softly lit sketch tools and night window blur
scale_reference: lamp base compared to pencil and cable connector
continuity_lock: matte white body, copper hinge, USB-C side port, same sketch-paper environment
must_preserve: final product clarity and compactness
avoid: fake logo, extra lamp, unrelated electronics, unreadable product shape
```

### Why This Works

- Product appears after a visible problem.
- Every feature is shown through hand operation or visible state change.
- The final shot locks material, hinge, port, product scale, and use context.
- It avoids unsupported claims and fake brand language.

### Common Bad Version

```markdown
做一个高级感桌面灯广告，多拍几个产品美图，光线很高级，最后来一个很酷的 packshot。
```

Why bad:

- No problem setup.
- No product operation.
- No proof detail.
- No continuity lock for hinge, port, material, or state.
- “高级感” gives style but not storyboard logic.

---

## Example 3: 七镜双人对白与权力转移

Use case: 电影叙事对白。重点是 master、OTS、reverse、reaction、insert、power shift、exit/consequence，而不是随机 close-up。

### Input Brief

夜晚厨房。母亲在餐桌一侧整理账单，成年女儿坐在对面，把一张录取通知书推到桌面中央。她想离开家去外地学习。母亲起初不看她，随后读到信，沉默，最后把信推回给她，表示同意。需要 7 个镜头。

### Spatial Lock

- 餐桌轴线：母亲在画面左侧，女儿在画面右侧。
- 母亲 eyeline 向右，女儿 eyeline 向左。
- 通知书在桌面中线。
- 不越轴。若需要重置，用俯拍 insert。

### Shot List Table

| Shot ID | Director Beat | Shot Purpose | Shot Size | Camera Angle | Lens Feel | Camera Movement | Action / Blocking | Composition / Depth | POV / Axis / Cut Logic | Scale / Continuity |
|---|---|---|---|---|---|---|---|---|---|---|
| SH_001 | 地理与关系 | 建立两人左右关系和沉默距离 | Medium wide master | eye-level across table | 35mm natural | locked-off | 母亲左侧看账单，女儿右侧握着信封 | 桌面中线分隔两人，吊灯压低空间 | 客观 master；母左女右；opening orientation | 通知书未露出；厨房夜灯方向锁定 |
| SH_002 | 行动触发 | 女儿把信推入冲突中心 | Insert | top-down table angle | graphic overhead | static | 信封从右推到桌面中线 | 手、信封、账单形成三角 | 俯拍中性重置；match on action | 信封小于账单，手从右入画 |
| SH_003 | 女儿主观压力 | 对齐女儿，等待母亲回应 | Clean single 女儿 | slight OTS from mother side | 50mm normal | slow push-in | 女儿看向母亲，手停在桌边 | 母亲肩膀虚焦前景，女儿中景 | 女儿对齐；eyeline 左；reaction wait | 同一右侧位置，信在两人之间 |
| SH_004 | 母亲拒看 | 母亲仍看账单，不接目光 | Clean single 母亲 | OTS from daughter side | 50mm normal | locked-off | 母亲视线落在账单，不看女儿 | 女儿手虚焦前景，母亲左侧 | reverse 保轴；eyeline 下而非右 | 母亲左侧，账单和信同桌面 |
| SH_005 | 信息证据 | 信件内容进入画面，但不长读文字 | Insert | top-down slight angle | macro-natural | static | 母亲手指停在录取通知书标题上 | 信纸中线，手指压住一角 | insert proof；不越轴 | 只保留短字：Admission Letter |
| SH_006 | 权力转移 | 母亲沉默后抬眼，情绪变化 | Close-up 母亲 | eye-level, clean single | 85mm compressed | slow dolly-in | 母亲抬眼看女儿，手仍压着信 | 背景厨房暗，脸和手分层 | power-shift close-up；eyeline 右 | 母亲左侧关系不变 |
| SH_007 | 后果 | 母亲把信推回给女儿，允许离开 | Two-shot medium | eye-level table side | 35mm natural | slow pullback | 母亲把信推向右侧，女儿接住 | 两人同框，信从左到右完成动作 | consequence；match action resolves axis | 信回到女儿手中；母左女右稳定 |

### Clean Handoff Specs

```yaml
SH_001
aspect_ratio: unspecified
scene: night kitchen table, silent family decision setup
duration: optional
dramatic_beat: distance and unspoken conflict are established before the letter appears
shot_purpose: establish geography, left/right relationship, table axis, and emotional distance
shot_size: medium wide master shot
camera_angle: eye-level across table
lens_feel: 35mm natural interior perspective
camera_movement: locked-off
cut_logic: opening orientation
panel_moment: decisive frame: mother looks at bills while daughter holds envelope
pov_alignment: objective observer
axis_of_action: table axis runs horizontally between mother on screen left and daughter on screen right
screen_direction: static; later letter movement will travel right-to-left then left-to-right
main_subject: mother and adult daughter seated across kitchen table
main_action: mother sorts bills while daughter hesitates with an envelope
blocking: mother seated left, daughter seated right, table center empty between them
body_pose: mother shoulders closed over papers; daughter upright, both hands holding envelope
eyeline: mother looks down at bills; daughter looks left toward mother
composition: table divides frame; mother left third, daughter right third, overhead lamp centered above gap
foreground: table edge and scattered bills
midground: mother, daughter, envelope in daughter's hands
background: dim kitchen cabinets and night window
scale_reference: normal hand-to-envelope and hand-to-bill scale
continuity_lock: mother always screen left, daughter screen right, kitchen night light, envelope begins in daughter's hands
must_preserve: table axis and emotional distance
avoid: crossing axis, extra family members, visible long dialogue text

SH_002
aspect_ratio: unspecified
scene: same kitchen table, letter enters conflict space
duration: optional
dramatic_beat: the daughter turns private intention into visible action
shot_purpose: show the triggering object moving into the center of the relationship
shot_size: insert shot
camera_angle: top-down table angle
lens_feel: graphic overhead, shallow tabletop depth
camera_movement: static
cut_logic: match on action from daughter's held envelope to the table insert
panel_moment: decisive moment: envelope stops at table centerline
pov_alignment: neutral geography reset
axis_of_action: overhead neutral; does not cross the dialogue axis
screen_direction: envelope moves from screen right toward center-left
main_subject: admission envelope sliding across kitchen table
main_action: daughter's hand pushes envelope toward the centerline between bills
blocking: daughter's hand enters from right, mother's bills remain left, envelope stops between them
body_pose: only hands visible; daughter's fingers release envelope at center
eyeline: not applicable
composition: envelope center, bills left, daughter's hand right, table grain horizontal
foreground: table surface and bill corners
midground: envelope and daughter's hand
background: soft edge of mother's hands near bills
scale_reference: envelope slightly smaller than folded bill stack
continuity_lock: same table, same bills, mother-left/daughter-right geography preserved
must_preserve: envelope as conflict object, not decorative prop
avoid: long readable legal text, new props, hand entering from wrong side

SH_003
aspect_ratio: unspecified
scene: same kitchen, daughter's waiting reaction
duration: optional
dramatic_beat: daughter waits for judgment after exposing her decision
shot_purpose: align viewer with daughter and show the emotional cost of waiting
shot_size: clean single medium close-up
camera_angle: slight OTS from mother's side, staying on correct axis
lens_feel: 50mm normal, intimate but not compressed
camera_movement: slow push-in
cut_logic: reaction cut after the letter lands
panel_moment: end frame: daughter holds still, eyes fixed left toward mother
pov_alignment: character-aligned with daughter, OTS subjective from mother side
axis_of_action: same table axis; camera remains on dialogue side
screen_direction: daughter's gaze travels right-to-left toward mother
main_subject: adult daughter sitting on screen right
main_action: she waits for her mother's response
blocking: daughter seated right of table, hands now empty near table edge, envelope visible lower left of her frame
body_pose: shoulders held high, hands flat near table edge, jaw tense
eyeline: left toward mother
composition: soft mother's shoulder edge in foreground left; daughter's face centered-right; letter low center
foreground: blurred edge of mother's shoulder and bill stack
midground: daughter's face, hands, envelope edge
background: dim kitchen wall and hanging lamp falloff
scale_reference: envelope width compared to daughter's hand
continuity_lock: daughter remains screen right, same sweater, same envelope on table center
must_preserve: quiet waiting, not melodramatic crying
avoid: over-the-top tears, axis flip, mother appearing on wrong side

SH_004
aspect_ratio: unspecified
scene: same kitchen, mother's refusal to look
duration: optional
dramatic_beat: mother resists the request by withholding eye contact
shot_purpose: show opposition through eyeline and body orientation rather than dialogue
shot_size: clean single medium close-up
camera_angle: OTS from daughter's side, staying on correct axis
lens_feel: 50mm normal
camera_movement: locked-off
cut_logic: reverse angle maintains dialogue axis and contrasts daughter's waiting with mother's avoidance
panel_moment: decisive frame: mother looks down at bills, not at daughter
pov_alignment: character-aligned with daughter watching mother
axis_of_action: same table axis; mother remains screen left
screen_direction: mother's potential eyeline would be left-to-right, but gaze stays down
main_subject: mother seated on screen left
main_action: mother continues touching bills instead of reading the envelope
blocking: mother left of table, bills in front, envelope just inside lower right frame
body_pose: chin lowered, one hand pinning bill stack, shoulders closed
eyeline: down at bills, avoiding daughter's gaze
composition: daughter's hand blurred foreground right; mother face left center; envelope lower edge
foreground: blurred daughter's hand and envelope corner
midground: mother's face, hands, bills
background: dark cabinets and sink light
scale_reference: bills and envelope normal tabletop size
continuity_lock: mother screen left, daughter offscreen right, envelope at table center, same night kitchen
must_preserve: refusal through withheld eyeline
avoid: mother smiling, looking directly at camera, changing table sides

SH_005
aspect_ratio: unspecified
scene: same table, letter proof insert
duration: optional
dramatic_beat: the object becomes legible enough to change the mother's response
shot_purpose: prove what the letter is without overloading the frame with text
shot_size: insert close-up
camera_angle: top-down slight angle on tabletop
lens_feel: macro-natural document detail
camera_movement: static
cut_logic: insert proof after mother's avoidance
panel_moment: decisive frame: mother's finger stops on the short title line
pov_alignment: neutral object proof
axis_of_action: overhead neutral reset
screen_direction: finger enters from left, letter points toward daughter on right
main_subject: admission letter under mother's finger
main_action: mother's fingertip rests on the title line of the letter
blocking: letter lies at table center; mother's hand from left touches paper; daughter's hand is absent
body_pose: only mother's finger and hand edge visible
eyeline: not applicable
composition: short title line centered; finger lower left; envelope edge upper right
foreground: mother's fingertip and paper texture
midground: letter title and envelope edge
background: blurred bill corner
scale_reference: finger width compared to printed title line
continuity_lock: same envelope and table; short readable text only: Admission Letter
must_preserve: object proof, not exposition dump
avoid: long readable paragraphs, different document, fake institution logo

SH_006
aspect_ratio: unspecified
scene: same kitchen, mother's power shift
duration: optional
dramatic_beat: mother moves from refusal to decision
shot_purpose: earn the close-up through a real change in control and emotion
shot_size: close-up
camera_angle: eye-level clean single on mother
lens_feel: 85mm compressed portrait feel
camera_movement: slow dolly-in
cut_logic: power-shift close-up after letter proof
panel_moment: end frame: mother finally looks up toward daughter
pov_alignment: character-aligned with daughter receiving mother's decision
axis_of_action: same table axis; mother remains screen left
screen_direction: mother's eyeline moves left-to-right toward daughter
main_subject: mother reading the letter and looking up
main_action: mother lifts her eyes from the paper to her daughter
blocking: mother still seated left, one hand still touching letter at table center
body_pose: chin rises slightly, lips pressed, fingers relaxed from the paper edge
eyeline: right toward daughter
composition: mother's face fills upper center; hand and letter blurred lower frame
foreground: soft edge of letter and mother's hand
midground: mother's face and eyes
background: dark kitchen blur
scale_reference: letter edge compared to hand, normal tabletop scale
continuity_lock: same mother screen side, same letter, same low kitchen light
must_preserve: quiet acceptance beginning, not sudden joy
avoid: crying breakdown, direct-to-camera stare, axis flip

SH_007
aspect_ratio: unspecified
scene: same kitchen, consequence and permission
duration: optional
dramatic_beat: the mother returns agency to the daughter
shot_purpose: resolve the scene through a visible action rather than explanatory dialogue
shot_size: medium two-shot
camera_angle: eye-level table side
lens_feel: 35mm natural interior feel
camera_movement: slow pullback
cut_logic: consequence after power shift; match action as the letter moves back
panel_moment: decisive moment: mother pushes letter back and daughter receives it
pov_alignment: objective observer with restored geography
axis_of_action: same table axis, mother screen left and daughter screen right
screen_direction: letter moves left-to-right from mother to daughter
main_subject: mother and daughter across the table
main_action: mother slides the letter back toward daughter and daughter catches it
blocking: mother left hand pushes paper; daughter right hand reaches forward from screen right
body_pose: mother shoulders soften; daughter leans forward slightly, fingers open to receive
eyeline: mother looks right toward daughter; daughter looks down at letter then up to mother
composition: two-shot with letter crossing the table center; overhead lamp frames the gap
foreground: table edge and bill stack
midground: mother's hand, letter, daughter's receiving hand
background: kitchen cabinets and night window
scale_reference: letter size compared to both hands
continuity_lock: mother left, daughter right, same table, same envelope/letter, same night kitchen
must_preserve: permission conveyed by action, no explanatory text needed
avoid: hugging in same shot, extra dialogue text, switching screen sides
```

### Why This Works

- The master shot establishes axis and left/right relation before singles.
- The insert is not filler; it proves what changes the mother's decision.
- The close-up is earned by a power shift.
- The final shot resolves with action, not abstract emotion.

### Common Bad Version

```markdown
做一个母女对话，先大全景，再几个过肩，再特写，最后感人一点。
```

Why bad:

- No dramatic trigger.
- No object proof.
- No eyeline or axis plan.
- Close-up is not earned.
- “感人” is not drawable blocking.

---

## Example 4: 四镜参考图转叙事分镜

Use case: 单张参考图作为锚点，不能把所有镜头都复制同一构图。

### Input Brief

参考图描述：竖构图夜雨街头，一个穿红雨衣的年轻女人站在透明伞下，位于画面右三分之一。湿地反射霓虹，背景有一辆模糊电车从左向右经过。用户要保留参考图气质，但加入一个小叙事：她发现地上一只发光纸鹤。4 个镜头，9:16。

### Reference Image Extraction

- function: first-frame / mood / wardrobe / rain / composition anchor
- visible subject: young woman, red raincoat, transparent umbrella
- shot size: full shot in vertical frame
- camera angle: eye-level street view
- lens feel: slight telephoto compression with layered neon reflections
- composition: subject right third, negative space and tram blur on left
- foreground: wet pavement reflection
- midground: woman and umbrella
- background: neon signs and tram moving left-to-right
- continuity to preserve: red raincoat, transparent umbrella, night rain, wet pavement, tram direction
- reinterpretation: add small glowing paper crane as narrative object

### Shot List Table

| Shot ID | Director Beat | Shot Purpose | Shot Size | Camera Angle | Lens Feel | Camera Movement | Action / Blocking | Composition / Depth | POV / Axis / Cut Logic | Scale / Continuity |
|---|---|---|---|---|---|---|---|---|---|---|
| SH_001 | 参考锚点 | 保留参考图核心机位与构图 | Full shot 9:16 | eye-level street view | slight telephoto | locked-off | 她站在伞下，电车从左向右模糊经过 | 人物右三分之一，左侧雨夜负空间 | 客观；tram left→right；opening anchor | 红雨衣、透明伞、湿地、夜雨锁定 |
| SH_002 | 叙事物出现 | 引入发光纸鹤并证明尺寸 | Low insert | pavement-level | macro / low wide | static | 纸鹤在红靴旁的雨水里发光 | 纸鹤前景，靴尖中景，霓虹倒影背景 | insert proof；从锚点切到细节 | 纸鹤小于靴宽；同一红色服装与雨地 |
| SH_003 | 主观发现 | 她注意到纸鹤 | Medium close-up | slight low angle under umbrella rim | portrait feel | slow push-in | 她低头看向伞缘下方 | 伞骨前景，脸中景，电车光斑背景 | 角色对齐；eyeline down-left | 红雨衣、透明伞、纸鹤光反在脸下方 |
| SH_004 | 空间关系收束 | 她蹲下拾起纸鹤，电车仍过 | High angle wide 9:16 | awning high angle | slight wide | slow pullback | 她一手扶伞，一手伸向纸鹤 | 上方雨棚前景，人物和纸鹤中景，电车背景 | geography reset；tram direction preserved | 纸鹤可夹在两指间；伞宽大于肩宽 |

### Key Handoff Spec Example

```yaml
SH_002
aspect_ratio: 9:16
scene: same rainy neon sidewalk, discovery insert
duration: optional
dramatic_beat: a small impossible object interrupts the still rain scene
shot_purpose: introduce the glowing paper crane and prove its small scale
shot_size: low insert
camera_angle: pavement-level looking across sidewalk
lens_feel: macro / low wide feel
camera_movement: static
cut_logic: insert proof after reference-anchor wide shot
panel_moment: decisive frame: crane glowing in puddle beside red boot
pov_alignment: objective object proof with character proximity
axis_of_action: street direction remains left-to-right in reflections
screen_direction: tram reflection continues left-to-right in background streak
main_subject: small glowing paper crane in rainwater
main_action: crane rests near the woman's red boot
blocking: woman's boot stops just behind the crane, toe angled toward it
body_pose: only boot edge visible
eyeline: not applicable
composition: crane foreground center; boot edge midground right; reflection line leads back
foreground: glowing paper crane and raindrops
midground: red boot edge and puddle ripple
background: soft neon reflection streaks and tram blur
scale_reference: crane smaller than the width of her boot
continuity_lock: red raincoat/boot color, transparent umbrella implied, night rain, wet pavement, tram left-to-right
must_preserve: crane as small delicate object; same rainy street world
avoid: crane becoming a bird, giant origami sculpture, dry pavement, changing coat color
```

### Why This Works

- The first shot respects the reference image as an anchor.
- The new object is introduced by scale and position, not vague “magic mood.”
- The derived shots change camera function: anchor → object proof → reaction → spatial payoff.
- Tram direction remains continuous.

### Common Bad Version

```markdown
根据参考图做四个电影感雨夜镜头，保持氛围，加入发光纸鹤。
```

Why bad:

- Does not define which reference facts matter.
- May copy the same poster composition four times.
- Does not lock paper crane scale or position.
- “氛围” cannot preserve tram direction, umbrella transparency, or red raincoat.

---

## Example 5: 六镜动作方向与越轴风险

Use case: 短动作场面，重点是 screen direction、障碍、接触、后果，而不是乱切。

### Input Brief

一个快递员在雨天骑自行车穿过窄巷，后方一只狗追来。他必须躲过倒下的垃圾桶，跳下车，把包裹递给门口老人。需要 6 个镜头，保持方向清楚。

### Spatial Lock

- 快递员始终从画面左向右前进。
- 狗从左后方追来，也沿左→右方向。
- 巷子纵深方向左后到右前。
- 不越轴；若要正面镜头，必须作为中性冲向镜头，不改变下一镜方向。

### Shot List Table

| Shot ID | Director Beat | Shot Purpose | Shot Size | Camera Angle | Lens Feel | Camera Movement | Action / Blocking | Composition / Depth | POV / Axis / Cut Logic | Scale / Continuity |
|---|---|---|---|---|---|---|---|---|---|---|
| SH_001 | 地理与追逐 | 建立巷子方向、骑手、狗 | Wide tracking | low alley side angle | 24mm wide | lateral tracking | 快递员骑车左→右，狗在后方追 | 前景水坑，中景车，背景狗和巷口 | 客观；axis left→right；opening geography | 黄色雨衣、红包裹箱、黑狗锁定 |
| SH_002 | 障碍出现 | 显示垃圾桶倒在路径上 | Insert / medium | ground-level ahead | wide foreground | static | 车轮接近倒下垃圾桶 | 垃圾桶前景，车轮中景 | obstacle insert；保持左→右 | 垃圾桶在右侧路径，占半个车道 |
| SH_003 | 决策瞬间 | 骑手决定跳车 | Medium close-up | side angle | 35mm natural | pan-follow | 骑手看向障碍，右脚离开踏板 | 人物中景，狗远背景 | reaction/action cut；不越轴 | 视线向右前方障碍 |
| SH_004 | 动作证明 | 跳下车避开障碍 | Full shot | low side angle | wide action feel | locked-off | 骑手从车上跳下，车轮擦过垃圾桶 | 水花前景，身体中景，垃圾桶右侧 | match on action；左→右继续 | 包裹箱仍背后，车未摔坏 |
| SH_005 | 压力接近 | 狗追近但不改变方向 | Compressed medium | rear-side angle | 85mm compressed | handheld follow | 狗冲过水坑，骑手抱包裹跑向门 | 狗中景，门在右侧背景 | escalation；same direction | 狗始终在骑手后方，不突然换边 |
| SH_006 | 后果与交付 | 追逐转为完成任务 | Medium two-shot | doorway eye-level | 35mm natural | slow stop | 快递员把包裹递给老人，狗停在门外 | 门框前景，递包中景，巷子背景 | consequence; direction resolves at door | 包裹完好；狗不攻击；方向收束 |

### Key Handoff Spec Example

```yaml
SH_004
aspect_ratio: unspecified
scene: rainy narrow alley, obstacle dodge action
duration: optional
dramatic_beat: the chase turns into a physical dodge without losing direction
shot_purpose: prove the rider avoids the fallen trash can through a clear body action
shot_size: full shot
camera_angle: low side angle from same side of alley axis
lens_feel: 24mm wide action feel, foreground water exaggerated
camera_movement: locked-off
cut_logic: match on action from decision to jump-off moment
panel_moment: decisive action moment: rider airborne beside bicycle as front wheel clears trash can
pov_alignment: objective action witness
axis_of_action: alley movement axis remains left-to-right; camera stays on same side
screen_direction: rider, bicycle, and dog all continue left-to-right
main_subject: courier in yellow raincoat jumping off bicycle
main_action: courier jumps sideways off the bike while the front wheel passes the fallen trash can
blocking: bicycle crosses center frame left-to-right; trash can blocks right-side path; courier body rises above bike frame
body_pose: one foot off pedal, knees bent, left hand still near handlebar, package box strapped behind
eyeline: toward landing point on right side of alley
composition: puddle splash foreground; courier and bicycle midground; dog and alley depth background
foreground: rain puddle splash and trash can rim
midground: courier, bicycle, red package box, fallen trash can
background: black dog chasing from left rear, narrow alley walls
scale_reference: trash can half the height of bicycle wheel; package box backpack-sized
continuity_lock: yellow raincoat, red package box, rainy alley, black dog behind, left-to-right direction
must_preserve: no axis flip; package remains attached; dog stays behind rider
avoid: crash gore, attacking dog bite, reversed direction, disappearing bicycle
```

### Why This Works

- Every action beat preserves left-to-right movement.
- Obstacle is introduced before the dodge.
- The jump is a decisive storyboard panel, not an unclear blur.
- Final shot converts chase energy into consequence and completion.

---

## Example 6: 十五秒快切服务广告结构

Use case: 快切广告，重点是节奏架构、每镜一个视觉工作、UI 可读、前后信息回收。

### Input Brief

15 秒广告：一个忙碌上班族打开冰箱，里面混乱。他用手机里的 meal planner 扫描食材，生成晚餐方案，然后快速做出一盘简单晚餐。不要 fake logo，不要抽象 AI claims。需要 15 个镜头，每镜有时长。

### Rhythm Structure

| Section | Shots | Timing | Function |
|---|---|---:|---|
| Hook chaos | SH_001-SH_003 | 2.1s | 快速显示问题。 |
| Scan setup | SH_004-SH_006 | 2.4s | 手机进入并扫描真实食材。 |
| Proof burst | SH_007-SH_011 | 4.1s | 食材变成具体步骤。 |
| Human result | SH_012-SH_013 | 2.2s | 人的轻松和成品晚餐。 |
| End lock | SH_014-SH_015 | 4.2s | 手机和晚餐一起收束。 |

### Shot List Table

| Shot ID | Duration | Director Beat | Shot Purpose | Shot Size | Camera Angle | Camera Movement | Action / Blocking | POV / Axis / Cut Logic | Scale / Continuity |
|---|---:|---|---|---|---|---|---|---|---|
| SH_001 | 0.7s | hook chaos | 冰箱混乱打断观众 | Wide | fridge POV | snap zoom out | 上班族打开塞满的冰箱 | opening hook | 绿色卫衣、菠菜、豆腐、胡萝卜、柠檬锁定 |
| SH_002 | 0.7s | overload | 显示决策疲劳 | Close-up | inside-fridge eye-level | handheld micro-shake | 他在食材间犹豫 | reaction cut | 同一人物和冰箱 |
| SH_003 | 0.7s | ingredient proof | 锁定后续会用的食材 | Extreme close-up | shelf level | static | 菠菜、豆腐、胡萝卜、柠檬挤在一层 | insert proof | 不加无关食材 |
| SH_004 | 0.8s | tool enters | 手机进入问题空间 | Medium close-up | OTS | tilt down | 他举起手机对准冰箱 | match action | 手机与手比例清楚 |
| SH_005 | 0.8s | scan proof | UI 对准真实食材 | Phone insert | straight-on | locked-off | 扫描框标出四种食材 | product-functional view | 无 fake logo，短标签 |
| SH_006 | 0.8s | conversion | 食材卡片生成 | Phone close-up | slight high angle | quick push-in | 四张 ingredient cards 叠起 | proof escalation | 标签短且可读 |
| SH_007 | 0.8s | recipe proof | 生成具体晚餐 | Phone close-up | straight-on | static | 屏幕显示 “15 min tofu stir-fry” | insert proof | 不写健康/减肥 claims |
| SH_008 | 0.8s | cook step 1 | 豆腐进入锅 | Close-up | counter side | whip-cut feel | 豆腐块倒入锅 | match on action | 豆腐来自冰箱 |
| SH_009 | 0.8s | cook step 2 | 胡萝卜进入流程 | Insert | top-down | static | 胡萝卜丝滑到砧板 | rhythm punctuation | 橙色清楚 |
| SH_010 | 0.8s | cook step 3 | 菠菜变成热菜 | Close-up | side pan angle | locked-off | 菠菜在蒸汽中变软 | proof burst | 菠菜仍可识别 |
| SH_011 | 0.9s | flavor proof | 柠檬加入 | Extreme close-up | side macro | static | 柠檬汁滴入锅 | insert punctuation | 柠檬来自冰箱 |
| SH_012 | 1.1s | relief | 人物压力下降 | Medium | kitchen island eye-level | slow pullback | 他把菜装盘，肩膀放松 | consequence | 同一绿色卫衣 |
| SH_013 | 1.1s | world response | 晚餐可分享 | Wide | table-height | locked-off | 家人手伸向盘子 | reaction/world proof | 菜品同一份 |
| SH_014 | 2.0s | app end lock | 手机和成品同框 | Close-up | table angle | slow push-in | 手机显示 completed recipe，旁边是晚餐 | end lock setup | 无 fake logo，UI 简短 |
| SH_015 | 2.2s | clarity | 混乱变成整齐计划 | Overhead wide | top-down | static | 手机、晚餐、剩余食材排成干净网格 | final resolution | 食材回收，画面简化 |

### Key Handoff Spec Example

```yaml
SH_005
aspect_ratio: 9:16
duration: 0.8s
scene: fridge interior, phone scan proof
dramatic_beat: the app turns messy ingredients into readable data
shot_purpose: show that the scan corresponds to real visible ingredients, not abstract AI magic
shot_size: phone insert
camera_angle: straight-on to phone screen
lens_feel: flat UI readable
camera_movement: locked-off
cut_logic: product-functional insert after the phone is raised toward the fridge
panel_moment: decisive frame: scan boxes align with spinach, tofu, carrot, lemon
pov_alignment: product-functional view
axis_of_action: not applicable; phone screen fills frame
screen_direction: static
main_subject: phone screen scanning fridge contents
main_action: simple boxes highlight spinach, tofu, carrot, lemon
blocking: hand grips phone edges; fridge contents visible behind/inside screen relationship
body_pose: fingers hold phone steadily at both sides
eyeline: not applicable
composition: phone screen fills frame; highlighted boxes align with food shapes
foreground: phone bezel and fingers
midground: screen UI boxes and short ingredient labels
background: blurred fridge contents
scale_reference: phone screen fills most of frame; labels large enough to read
continuity_lock: same four ingredients from fridge: spinach, tofu, carrot, lemon; no fake brand logo
must_preserve: readable scan relationship and short labels
avoid: dense tiny UI, fake app logo, hologram outside phone, unrelated ingredients, health claims
```

### Why This Works

- The structure is not “15 cool shots”; it has hook, setup, proof burst, response, end lock.
- Every quick shot has one job.
- Ingredients introduced in the fridge return as cards and cooking steps.
- UI text is short and avoids unsupported claims.

### Common Bad Version

```markdown
做一个快节奏 AI app 广告，很多未来感 UI，快速切换冰箱、做饭、开心家庭，最后 app 画面。
```

Why bad:

- Speed without rhythm architecture.
- Futuristic UI risks fake holograms and unreadable screens.
- No ingredient continuity.
- No proof that the app transformed specific items into dinner.

---

## Example 7: Good Revision Behavior

Use case: 用户要求修改镜头表时，保持 ID 稳定，不乱重排。

### User Revision

“SH_003 太弱，更有导演感，但不要改镜头数量。”

### Bad Revision

```markdown
我重新设计一版：SH_001、SH_002、SH_003、SH_004 全部换掉……
```

Why bad:

- It destroys stable IDs.
- It changes approved shots unnecessarily.
- It may break continuity already established.

### Good Revision

```markdown
保留 SH_001、SH_002、SH_004。只强化 SH_003：把它从普通反应特写改为“权力转移 close-up”。

SH_003 Revised
Director Beat: 母亲从拒绝转为决定
Shot Purpose: 让特写由信息变化触发，而不是泛泛情绪
Shot Size: close-up
Camera Angle: eye-level clean single on mother
Lens Feel: 85mm compressed portrait feel
Camera Movement: slow dolly-in
Action / Blocking: 母亲手指还压着录取通知书，抬眼看向女儿
Composition / Depth: 信纸模糊在下前景，母亲脸在中景，厨房背景压暗
POV / Axis / Cut Logic: power shift after insert proof；母亲仍在 screen left，eyeline 向右
Scale / Continuity: 同一信纸、同一夜晚厨房、母左女右不变
```

Why good:

- It preserves IDs.
- It improves director logic, not just style.
- It keeps axis, eyeline, and continuity stable.
- It identifies why the old shot was weak and what changed.

---

## Global Bad Pattern: Prompt Poetry

Bad:

```markdown
A cinematic, emotional, premium, dramatic, beautiful shot with deep atmosphere and stunning composition.
```

Correction:

```markdown
Medium close-up at eye level. The character stands screen right, hand still on the door handle, gaze down-left toward the envelope on the floor. Door frame in foreground, envelope in midground, dark hallway background. Cut logic: reaction after object reveal. Continuity: same coat, wet hair, hallway light from camera left. Avoid: open-mouth shock, extra characters, unreadable envelope.
```

The correction is better because it defines frame size, camera relation, blocking, eyeline, layers, cut logic, continuity, and avoid notes.
