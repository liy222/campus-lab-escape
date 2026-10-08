# Campus Lab Escape v4 最终画面与交互实施文档
## 固定视角 2D 密室方案（Rusty Lake / Cube Escape 表现逻辑参考）

项目仓库：`liy222/campus-lab-escape`  
当前仓库基线：`main` / v3.4 灰盒完成  
当前版本信息：关卡 `3.4.0`，Schema `1.4.0`  
当前已验收标签：`v3.4-graybox-complete`  
当前 v3.4 提交：`49a2f925a78055552781685e79ee96496bb9bdd6`

> 本文基于仓库当前 `README.md`、`STATUS.md`、`docs/upgrade-plan.md`、`frontend/src/App.tsx`、`frontend/src/Assistant.tsx`、`frontend/src/api.ts`、`backend/app/domain/puzzle_rules.py`、`backend/app/domain/mini_rules.py`、`backend/app/domain/graybox_rules.py`、`backend/app/domain/device_flow.py` 的实际实现整理。
>
> 本方案不复制 Rusty Lake / Cube Escape 的具体房间、素材、角色、谜题或 UI；只借鉴“固定视角 2D 房间、克制信息密度、低饱和手绘感、点击进入局部特写”的表现逻辑，并以校园实验室、现代设备谜题和 AI 探索伙伴形成项目自己的视觉语言。

---

# 1. 当前项目状态

## 1.1 已完成部分

仓库当前已经完成 v3.0–v3.4：

- v3.0：降低信息暴露
- v3.1：多状态设备
- v3.2：三房间谜题网络
- v3.3：电路与顺序小游戏
- v3.4：三级 AI 提示、统计、隐藏线索、结算

当前 v3.4 已具备完整可玩的灰盒逻辑，并已通过仓库记录中的独立 QA。

当前后端仍然是游戏规则权威来源，已有：

- 三房间状态
- 道具生命周期
- 物体观察状态
- 多阶段设备状态
- 电路小游戏
- 顺序小游戏
- AI 三级提示
- 错误计数
- 提示计数
- 线索计数
- 隐藏线索
- S/A/B/C 结算评级
- 保存 / 恢复 / 重置

因此 v4 **不重新设计玩法，也不重写后端**。

---

## 1.2 当前前端状态

当前前端技术栈：

```text
React 19.2
TypeScript 5.9
Vite 7.2
```

当前 `frontend/package.json` 尚未包含 Phaser。

现有 `App.tsx` 已经实现：

- 场景热点
- 物体选择
- 背包
- 线索笔记
- 登录表单
- 密码输入
- 3×3 电路小游戏
- 四设备顺序小游戏
- 保存/恢复/重置
- 结算
- 行动历史

`Assistant.tsx` 已实现：

- 免费 mock
- DeepSeek
- L1/L2/L3 提示强度
- 提示次数显示
- API Key 临时内存保存
- 只引用已发现线索

这些逻辑全部保留。

v4 的目标不是替换这些功能，而是：

> **把“网页式面板交互”替换为“游戏式场景交互”。**

---

# 2. 最终视觉方向

## 2.1 定义

最终画面采用：

> **固定视角 2D 校园实验室密室 + 低饱和轻旧化手绘风 + 少量局部动画 + 设备特写 + 极简常驻 UI**

核心参考逻辑：

```text
房间总览
↓
点击关键物件
↓
进入局部特写
↓
观察 / 使用道具 / 解谜
↓
返回房间
↓
场景状态发生变化
```

---

## 2.2 不采用

明确不做：

- WASD 移动
- 第一人称自由相机
- 完整 3D
- 大幅镜头旋转
- 大量粒子
- 大面积 Bloom
- 高写实 PBR
- RPG UI
- 常驻网页式侧栏
- 所有可交互物体永久发光

---

# 3. 美术视觉规范

## 3.1 关键词

```text
固定视角
平面手绘
低饱和
轻微旧化
灰绿
灰蓝
米灰
暗棕
夜间校园
安静
理性
神秘
非恐怖
克制
```

---

## 3.2 色彩

### 主色

| 用途 | 色彩方向 |
|---|---|
| 墙面 | 米灰 / 冷灰 |
| 实验柜 | 灰绿 / 暗橄榄绿 |
| 金属设备 | 蓝灰 / 中性灰 |
| 地面 | 冷灰 |
| 木质 | 暗棕 |
| 夜景 | 深蓝 / 蓝黑 |
| 纸张 | 旧纸米黄 |

### 状态强调色

| 状态 | 色彩 |
|---|---|
| 电气警告 | 黄 |
| 锁定 / 错误 | 暗红 |
| 通过 / 通电 | 低饱和绿 |
| 月光 / 屏幕 | 冷蓝 |
| 室内局部光 | 暖黄 |

---

## 3.3 线条

- 主要物体有明确深色轮廓。
- 线宽统一。
- 背景轮廓比前景略弱。
- 不做漫画式粗黑边。
- 不追求真实照片边缘。

---

## 3.4 纹理

只允许轻量纹理：

- 墙面颗粒
- 纸张旧化
- 金属轻微划痕
- 柜体少量掉漆
- 地面轻微污渍

避免：

- 高频噪点
- 随机脏污
- AI 式无意义细节
- 过多装饰
- 写实镜面高光

---

# 4. 画面与交互总原则

## 4.1 每个房间只保留 5–8 个视觉重点

当前后端虽然有多个对象，但主画面不能把所有内容做成同等视觉权重。

优先级：

```text
一级：本房间主要谜题
二级：跨房间线索
三级：状态设备
四级：氛围道具
```

---

## 4.2 默认不显示热点

普通状态：

- 不显示黄色圆圈
- 不显示发光边框
- 不显示“点击这里”
- 不显示工具提示

Hover 时：

- 光标变化
- 对象亮度增加约 5–10%
- 可选极轻微描边

---

## 4.3 点击行为

点击物件后不要打开网页卡片。

采用：

### 小对象

直接进入特写。

例如：

```text
墙钟
实验记录
铭牌
维护说明
对应表
```

### 设备

进入独立设备场景。

例如：

```text
显微镜
储物柜
电源箱
电脑
终检控制台
出口门
```

---

# 5. 当前后端状态必须保持不变

v4 画面必须映射现有服务器状态，而不是在 Phaser 中重新建立另一套游戏规则。

当前核心状态：

## 储物柜

```text
LOCKED
→ CODE_ACCEPTED
→ OPEN
→ ITEM_TAKEN
```

## 电源箱

```text
CLOSED
→ OPEN
→ MISSING_FUSE
→ FUSE_INSTALLED
→ CIRCUIT_READY
→ POWER_ON
```

## 电脑

```text
OFF
→ BOOTING
→ LOGIN_LOCKED
→ UNLOCKED
→ DATA_READ
```

## 最终出口

```text
LOCKED
→ CARD_ACCEPTED
→ FINAL_CHECK
→ UNLOCKED
→ OPEN
```

## 显微镜

```text
EMPTY
→ SLIDE_PLACED
```

## Room 3 面板

```text
EMPTY
→ STRIP_INSERTED
```

任何视觉动画都必须在服务器动作成功后播放。

---

# 6. Room 1：实验准备室

仓库当前定义：

```text
room_id: R1
名称：实验准备室
描述：月光落在实验桌上，墙钟的指针停在深夜。
```

---

# 6.1 Room 1 当前真实对象

| object_id | 游戏对象 | 类型 |
|---|---|---|
| `r1_clock` | 墙钟 | clue |
| `r1_record` | 实验记录 | clue |
| `r1_plaque` | 实验室铭牌 | clue |
| `r1_microscope` | 显微镜 | device |
| `sample_slide` | 样本玻片 | item |
| `r1_cabinet` | 储物柜 | container |
| `r1_door` | 设备间门 | door |
| `r1_symbols` | 柜内旧标签 | clue |
| `r1_fuse` | 保险丝 | item |
| `r1_photo` | 柜内凹槽 / 旧相片 | v3.4 隐藏线索 |

---

# 6.2 Room 1 最终主画面

推荐正视构图：

```text
┌────────────────────────────────────┐
│                                    │
│   月夜窗户       墙钟        铭牌   │
│                                    │
│          ┌──────────────┐          │
│          │   实验桌      │          │
│          │ 显微镜 记录   │          │
│          │  玻片         │          │
│          └──────────────┘          │
│                                    │
│  储物柜                       门    │
│                                    │
└────────────────────────────────────┘
```

底部只有极简背包栏。

---

# 6.3 Room 1 美术重点

### 左侧：窗户

表现：

- 深蓝夜空
- 月亮
- 远处校园建筑轮廓
- 少量暖黄色窗灯
- 树影

作用：

- 建立“校园”
- 建立“夜间”
- 建立氛围

窗外内容不作为谜题热点。

---

### 中央：实验桌

视觉中心。

必须包含：

- 显微镜
- 实验记录
- 样本玻片

不要加入大量瓶罐。

只增加 2–3 个弱化的实验环境物体即可。

---

### 上方：墙钟

必须能一眼看清：

```text
21:17
```

但不要做成巨大谜题提示。

点击进入墙钟特写后才清楚看到：

> “实验开始”

---

### 墙边：LAB-42 铭牌

主画面上存在，但视觉权重低于显微镜和墙钟。

点击特写：

```text
LAB-42
```

这是跨房间登录线索。

---

# 6.4 Room 1 谜题视觉流程

## A. 样本玻片

初始：

```text
桌边玻片盒
```

观察后可拾取。

拾取成功：

- 玻片从场景消失
- 0.25–0.4 秒缩小
- 飞入底部背包槽

---

## B. 显微镜

### EMPTY

主场景：

- 载物台空

特写：

```text
显微镜
玻片夹
空载物台
```

玩家选择背包里的 `sample_slide` 后点击载物台。

后端：

```text
use_item(sample_slide, r1_microscope)
```

成功后：

```text
SLIDE_PLACED
```

视觉：

- 玻片出现在载物台
- 背包中的玻片消失

再次点击目镜：

显示圆形显微视野：

```text
LAB SAMPLE 42
```

对应现有线索：

`r1_sample_clue`

---

## C. 墙钟 + 实验记录

墙钟特写：

```text
21:17
实验开始
```

实验记录特写：

> 样本索引的前两位是样本编号，最后两位采用实验开始时间的分钟数。

组合：

```text
42 + 17
= 4217
```

---

## D. 储物柜

主场景状态：

### LOCKED

柜门关闭。

点击进入：

```text
柜门
四位机械/数字锁
“样本索引”
```

输入：

```text
4217
```

后端 `submit_code` 成功：

```text
CODE_ACCEPTED
```

视觉：

- 绿灯短亮
- 金属“咔哒”

服务器尚未打开柜门。

玩家再次点击把手：

后端 `interact`

```text
OPEN
```

动画：

- 柜门 300–450ms 打开

柜内出现：

- 保险丝 `r1_fuse`
- 批次标签 `r1_symbols`

标签：

```text
▲ ● ■ ★
```

保险丝取走后：

```text
ITEM_TAKEN
```

此时 v3.4 隐藏对象 `r1_photo` 才出现。

表现：

> 原本放保险丝的位置下面露出一道浅凹槽。

点击凹槽：

显示旧合照和故事文字。

不能提前显示隐藏相片。

---

## E. Room 1 → Room 2

当前仓库 `r1_door` 是普通门闩逻辑，不需要门禁卡。

玩家观察后：

- 点击门闩
- 服务器 `interact`
- `r2_unlocked = true`

视觉：

- 门闩滑开
- 门可进入

不要把门画成需要刷卡的门，避免与当前后端逻辑冲突。

---

# 7. Room 2：设备实验室

仓库当前定义：

```text
room_id: R2
名称：设备实验室
描述：仪器沿墙排列，安静的屏幕映着房间里的微光。
```

---

# 7.1 Room 2 当前真实对象

| object_id | 对象 |
|---|---|
| `r2_powerbox` | 电源箱 |
| `r2_monitor` | 电脑 |
| `r2_maintenance` | 维护说明 |
| `r2_door` | 控制室门 |
| `research_strip` | 研究纸条 |
| `access_card` | 门禁卡 |
| `r2_service_label` | 箱背维护签（隐藏线索） |

注意：

当前 v3.2+ 保险丝来自 Room 1 的储物柜，而不是 Room 2 桌面。

---

# 7.2 Room 2 主画面

推荐构图：

```text
┌────────────────────────────────────┐
│                                    │
│   工作台 / 维护说明        电脑     │
│                                    │
│                 电源箱             │
│                                    │
│                                    │
│                             控制室门│
│                                    │
└────────────────────────────────────┘
```

整体比 Room 1 更暗。

---

# 7.3 Room 2 核心视觉：通电前后

## POWER OFF

初始：

- 主灯关闭
- 电源箱局部可见
- 电脑完全黑屏
- 环境为深蓝灰
- 只保留很弱的应急环境光

---

## POWER ON

完成电路并拉下总闸后：

```text
灯管闪一下
↓
主灯点亮
↓
电脑电源灯亮
↓
环境从深蓝灰变成灰蓝
```

音效：

```text
咔
低频电流声
灯管轻响
电脑风扇
```

不要：

- 大火花
- 爆炸
- 强 Bloom

---

# 7.4 电源箱完整视觉状态

## CLOSED

主画面：

- 金属箱门关闭

点击特写：

```text
箱盖
搭扣
⚡警告
```

点击搭扣：

服务器 `interact`

→ `OPEN`

---

## OPEN

箱盖打开。

里面仍有护板。

玩家点击护板：

服务器 `interact`

→ `MISSING_FUSE`

---

## MISSING_FUSE

显示：

- 两枚触点
- 中间空槽
- 总闸处于抬起状态

玩家选择背包 `fuse`：

```text
use_item(fuse, r2_powerbox)
```

→ `FUSE_INSTALLED`

---

## FUSE_INSTALLED

显示：

- 保险丝插入
- 3×3 线路模块
- 总闸锁定

这时直接进入当前已经实现的线路小游戏。

---

# 7.5 3×3 线路小游戏画面

当前仓库已经有真实：

```text
3 rows
3 columns
I / L 两类模块
rotation 0–3
source
sink
```

v4 只换视觉。

表现：

```text
┌───────────────┐
│ 电源端         │
│  □ □ □        │
│  □ □ □        │
│  □ □ □        │
│         主系统 │
└───────────────┘
```

模块：

- I：直线电路
- L：直角电路

点击：

- 顺时针旋转 90°

服务器仍执行：

```text
rotate_circuit
submit_circuit
```

成功后：

```text
CIRCUIT_READY
```

绿灯亮。

玩家拉下总闸：

```text
interact(r2_powerbox)
```

→ `POWER_ON`

---

# 7.6 隐藏线索：箱背维护签

当前 v3.4：

只有：

```text
powerbox == POWER_ON
```

才出现：

`r2_service_label`

所以视觉上必须严格延迟。

通电后：

- 电箱内部一盏小指示灯亮
- 光线让箱体背后一张泛黄标签可见

点击才加入笔记。

---

# 7.7 电脑视觉流程

## OFF

黑屏。

点击电源键。

服务器：

```text
interact
```

→ `BOOTING`

---

## BOOTING

屏幕：

```text
LAB SYSTEM
BOOT...
```

短动画约 0.5–1 秒即可。

再次继续：

→ `LOGIN_LOCKED`

---

## LOGIN_LOCKED

显示：

```text
LAB TERMINAL

USER:
PASS:
```

不要使用现代网页登录框。

设计成：

- 黑绿 CRT / 老终端
- 等宽字体
- 简单光标

当前真实答案来自已有线索：

```text
USER = LAB-42
PASS = 2117
```

依据：

- Room 1 铭牌
- Room 1 墙钟
- Room 2 维护说明

---

## UNLOCKED

显示：

```text
AUTH OK

ARCHIVED RESEARCH RECORD
[OPEN]
```

点击读取：

服务器 `interact`

→ `DATA_READ`

---

## DATA_READ

电脑旁小托盘/侧边托架打开。

出现：

- `research_strip`
- `access_card`

两者要做成场景对象，而不是直接弹进背包。

玩家分别观察、拾取。

---

# 7.8 Room 2 → Room 3

当前 `r2_door` 同样是普通门闩逻辑。

不要在画面中设计成“需要应急钥匙”。

当前 v3.4 已经没有旧版 `emergency_key` 路线。

点击门闩后：

```text
r3_unlocked = true
```

进入 Room 3。

---

# 8. Room 3：出口控制室

仓库当前定义：

```text
room_id: R3
名称：出口控制室
描述：控制台旁有一张设备对应表，出口门立在走廊尽头。
```

---

# 8.1 Room 3 当前真实对象

| object_id | 对象 |
|---|---|
| `r3_legend` | 设备对应表 |
| `r3_panel` | 终检控制台 |
| `exit_door` | 实验室出口 |

Room 3 视觉必须比前两个房间更简洁。

---

# 8.2 Room 3 主画面

```text
┌────────────────────────────────────┐
│                                    │
│   设备对应表       终检控制台       │
│                                    │
│                                    │
│                        最终出口门   │
│                                    │
└────────────────────────────────────┘
```

不要再放大量：

- 试剂瓶
- 显微镜
- 书本
- 实验桌装饰

目标：

> 玩家一进入就知道最终挑战围绕控制台和出口。

---

# 8.3 设备对应表

当前 v3.3 实际规则：

```text
■ = 通风
▲ = 冷却
★ = 照明
● = 安全
```

Room 1 已获得：

```text
源序：
▲ ● ■ ★
```

研究纸条：

```text
读取：
第3 → 第1 → 第4 → 第2
```

因此：

```text
■ ▲ ★ ●
```

对应设备：

```text
通风 → 冷却 → 照明 → 安全
```

这就是当前真实顺序小游戏答案来源。

视觉上不要直接在面板显示正确顺序。

---

# 8.4 研究纸条插入

玩家拥有 `research_strip`。

观察 `r3_panel` 后：

```text
use_item(research_strip, r3_panel)
```

服务器：

```text
panel:
EMPTY
→ STRIP_INSERTED
```

动画：

- 窄纸沿定位槽滑入控制台
- 控制台四个设备按钮亮起

---

# 8.5 出口门禁卡

玩家从 Room 2 获得 `access_card`。

对 `exit_door` 使用：

```text
use_item(access_card, exit_door)
```

状态：

```text
LOCKED
→ CARD_ACCEPTED
```

视觉：

- 读卡器绿灯闪一次
- 门仍不开

这点必须表现清楚：

> 刷卡只是激活终检，不是直接开门。

---

# 8.6 启动终检

玩家操作出口：

```text
interact(exit_door)
```

状态：

```text
CARD_ACCEPTED
→ FINAL_CHECK
```

此时 Room 3 顺序小游戏才真正进入可提交阶段。

---

# 8.7 顺序小游戏

当前真实设备：

| symbol | device |
|---|---|
| ▲ | 冷却 |
| ★ | 照明 |
| ● | 安全 |
| ■ | 通风 |

画面：

```text
[ ▲ 冷却 ]
[ ★ 照明 ]
[ ● 安全 ]
[ ■ 通风 ]
```

玩家依次按下四个按钮。

当前正确顺序：

```text
通风
→ 冷却
→ 照明
→ 安全
```

即：

```text
■ → ▲ → ★ → ●
```

服务器：

```text
submit_sequence
```

成功：

```text
check_done = true
```

视觉：

- 四个小灯依次亮
- 最终“终检通过”灯变绿

---

# 8.8 最终门

终检通过后：

当前状态：

```text
FINAL_CHECK
```

玩家点击：

```text
interact
```

→ `UNLOCKED`

音效：

```text
锁舌回缩
金属咔哒
```

再次点击：

→ `OPEN`

动画：

- 门缓慢打开 0.8–1.5 秒
- 走廊暖光进入房间

然后玩家点击出口：

```text
move(EXIT)
```

服务器：

```text
status = won
```

---

# 9. 隐藏线索表现

当前 v3.4 共有：

```text
clues_total = 10
hidden_total = 2
```

隐藏线索：

## Room 1

`r1_photo_clue`

触发条件：

```text
cabinet == ITEM_TAKEN
```

表现：

保险丝取走后才露出凹槽。

---

## Room 2

`r2_service_clue`

触发条件：

```text
powerbox == POWER_ON
```

表现：

通电后的灯光才照出维护签。

---

# 10. AI 探索伙伴最终 UI

当前 AI 系统已经完成三级提示。

保留逻辑，不重写。

主场景只显示一个很小的入口：

```text
💬
```

推荐右下角。

点击后：

- React 抽屉从右侧滑出
- 不离开 Phaser 场景
- 背景轻微暗化

---

## 10.1 AI 面板必须保留的功能

当前仓库已有：

- mock / DeepSeek 选择
- L1 / L2 / L3
- API Key 输入
- 已使用提示次数
- 回答
- 引用的已发现线索
- 服务错误反馈

这些保留。

---

## 10.2 AI 面板视觉

不要像 ChatGPT。

推荐：

```text
LAB ASSIST
────────────
提示等级：L1 L2 L3

[问题输入区域]

[获取提示]
```

风格：

- 旧实验终端
- 灰绿
- 纸张记录夹
- 或小型通信设备

---

# 11. 线索笔记 UI

当前所有线索都由服务器 `state.clues` 提供。

主画面不常驻显示。

点击：

```text
📒
```

打开全屏/侧页笔记。

设计：

- 旧实验记录本
- 左右翻页
- 每页 1–2 条线索
- 标题 + 原始文字

不要替玩家自动组合答案。

例如不能写：

```text
42 + 17 = 4217
```

除非这是玩家自己已经完成的谜题结果。

---

# 12. 背包 UI

底部固定小栏：

```text
┌───────────────────────┐
│ [ ] [ ] [ ] [ ]       │
└───────────────────────┘
```

当前真实道具：

```text
sample_slide
fuse
research_strip
access_card
```

最多只需要 4–5 个槽。

---

## 12.1 道具交互

推荐：

```text
点击道具
↓
道具槽高亮
↓
点击场景目标
↓
use_item
```

而不是：

```text
打开网页下拉框
选择目标
```

错误组合时：

- 不取消道具选择
- 显示一句短反馈
- 播放轻微失败音
- v3.4 后端负责 mistake_count

---

# 13. 保存 / 恢复 / 新游戏

当前功能保留，但移出主游戏页面。

放入：

```text
⚙ 菜单
```

菜单：

```text
继续游戏
保存进度
恢复存档
重新开始
新游戏
返回
```

不要在主场景下方长期展示保存面板。

---

# 14. 结算画面

当前服务器结算包含：

```text
elapsed_seconds
clues_found / 10
hint_count
mistake_count
hidden_found / 2
rating
```

最终结算应该使用独立全屏画面。

示例：

```text
逃离成功

用时            00:22:46
发现线索        9 / 10
隐藏发现        1 / 2
AI 提示         2
错误尝试        3

评级

        A

[重新开始]   [返回记录]
```

评级规则继续完全使用后端当前逻辑。

---

# 15. Phaser 与 React 最终职责

## Phaser

负责：

- 房间背景
- Sprite
- 热点
- Hover
- 房间内视觉状态
- 特写场景
- 小游戏画面
- 动画
- 音效
- 门/柜子/电箱等状态表现

## React

继续负责：

- API
- VisibleState
- Session
- 背包 UI
- 线索笔记
- AI
- 设置
- 保存/恢复
- 结算
- 网络错误
- 状态同步

## FastAPI / domain

继续负责：

- 所有真实规则
- 谜题答案
- 道具是否合法
- 设备状态
- 房间是否解锁
- 错误统计
- 提示统计
- 保存
- 结算

---

# 16. 推荐前端结构

v4.0 开始后：

```text
frontend/src/
├── App.tsx
├── Assistant.tsx
├── api.ts
├── main.tsx
├── style.css
│
├── game/
│   ├── GameCanvas.tsx
│   ├── config.ts
│   ├── bridge.ts
│   │
│   ├── scenes/
│   │   ├── BootScene.ts
│   │   ├── Room1Scene.ts
│   │   ├── Room1MicroscopeScene.ts
│   │   ├── Room1CabinetScene.ts
│   │   ├── Room2Scene.ts
│   │   ├── Room2PowerboxScene.ts
│   │   ├── Room2TerminalScene.ts
│   │   ├── Room3Scene.ts
│   │   ├── Room3PanelScene.ts
│   │   └── VictoryScene.ts
│   │
│   ├── systems/
│   │   ├── SceneStateSync.ts
│   │   ├── InteractionSystem.ts
│   │   ├── AudioSystem.ts
│   │   └── TransitionSystem.ts
│   │
│   └── mappings/
│       ├── room1.ts
│       ├── room2.ts
│       └── room3.ts
│
├── components/
│   ├── InventoryBar.tsx
│   ├── NotebookDrawer.tsx
│   ├── AssistantDrawer.tsx
│   ├── GameMenu.tsx
│   ├── NoticeToast.tsx
│   └── SettlementScreen.tsx
│
└── assets/
    ├── room1/
    ├── room2/
    ├── room3/
    ├── ui/
    ├── items/
    └── audio/
```

---

# 17. React ↔ Phaser 桥接

禁止 Phaser 自己维护后端真状态。

推荐：

```text
Phaser 点击 object_id
↓
bridge.emit("object-click", object_id)
↓
React 根据 VisibleState 决定行为
↓
React 调 API
↓
服务器返回新的 VisibleState
↓
React 更新
↓
SceneStateSync 将新状态传给 Phaser
↓
Phaser 播放对应视觉变化
```

---

# 18. 当前 action 与 v4 视觉动作映射

| 后端 tool | v4 表现 |
|---|---|
| `inspect` | 进入特写 / 显示观察结果 |
| `take` | 拾取动画 → 背包 |
| `use_item` | 道具选中 → 点击目标 |
| `interact` | 柜门、门闩、开关等动画 |
| `submit_code` | 数字锁特写 |
| `submit_login` | 终端登录 |
| `rotate_circuit` | 电路模块旋转 |
| `submit_circuit` | 电路确认 |
| `submit_sequence` | Room 3 设备顺序 |
| `move` | 房间淡出/切换 |
| `get_inventory` | 不需要单独场景，背包直接显示 |

---

# 19. 素材拆分

原则：

> 静态背景合并，状态对象单独拆。

不要把整个房间所有状态画成一张图。

---

# 19.1 Room 1

```text
assets/room1/

bg.png
window_night.png

clock.png
record.png
plaque.png

microscope_empty.png
microscope_slide.png

sample_slide.png

cabinet_locked.png
cabinet_accepted.png
cabinet_open.png
cabinet_empty.png

cabinet_symbols.png
fuse.png
photo_hidden.png
photo_revealed.png

door_closed.png
door_unlatched.png
```

特写：

```text
closeup_clock.png
closeup_record.png
closeup_plaque.png

closeup_microscope_empty.png
closeup_microscope_slide.png
microscope_view_42.png

closeup_cabinet_locked.png
closeup_cabinet_open.png
```

---

# 19.2 Room 2

```text
assets/room2/

bg_dark.png
light_overlay_on.png

powerbox_closed.png
powerbox_open.png
powerbox_missing_fuse.png
powerbox_fuse.png
powerbox_ready.png
powerbox_power_on.png

monitor_off.png
monitor_booting.png
monitor_login.png
monitor_unlocked.png
monitor_data.png

maintenance_note.png
research_strip.png
access_card.png

service_label_hidden.png
service_label_visible.png

door_closed.png
door_unlatched.png
```

---

# 19.3 Room 3

```text
assets/room3/

bg.png

legend.png

panel_empty.png
panel_strip.png
panel_active.png
panel_complete.png

exit_locked.png
exit_card.png
exit_finalcheck.png
exit_unlocked.png
exit_open.png
```

---

# 20. 分辨率

最终桌面基准：

```text
1920 × 1080
16:9
```

游戏内部可使用逻辑分辨率：

```text
1600 × 900
或
1920 × 1080
```

Phaser 使用：

```text
FIT
CENTER_BOTH
```

关键交互对象不能贴边。

---

# 21. 字体

建议两类：

## 普通 UI

清晰中文无衬线。

## 游戏内纸张 / 实验记录

可使用轻微手写感或打字机感，但必须确保中文可读。

终端：

- 等宽字体

不要：

- 大量花体
- 过度恐怖字体
- 低清像素中文

---

# 22. 动画

固定视角不代表完全静止。

推荐：

## Room 1

- 月光极轻微变化
- 树影缓慢移动
- 柜门打开
- 道具拾取

## Room 2

- 电源灯
- 线路模块旋转
- 主灯通电
- 电脑启动

## Room 3

- 状态灯
- 设备按钮
- 门锁
- 出口开启

---

# 23. 音效

## Room 1

- 夜间环境
- 很轻的风
- 纸张
- 柜门
- 金属锁

## Room 2

- 电箱门
- 保险丝卡入
- 电路按钮
- 总闸
- 电流
- 电脑风扇
- 键盘

## Room 3

- 门禁刷卡
- 按钮
- 错误提示
- 成功提示
- 门锁回缩
- 最终门开启

---

# 24. v4.0 实施范围

只做 Room 1。

必须完成：

- Phaser 接入
- React/Phaser bridge
- Room 1 主场景
- Room 1 所有真实 object_id 热点
- 显微镜特写
- 墙钟特写
- 实验记录特写
- 铭牌特写
- 储物柜密码锁
- 柜门状态
- 保险丝
- 批次标签
- 隐藏相片
- Room 1 → R2 转场
- 底部背包栏
- 笔记抽屉
- AI 抽屉
- 菜单

---

# 25. v4.0 验收门槛

Room 1 必须达到：

1. 完全不依赖当前网页卡片布局也能完成 Room 1。
2. 后端 v3.4 规则不改变。
3. `VisibleState` 仍是唯一状态来源。
4. 所有道具与线索正常进入后端状态。
5. 保存、刷新、恢复后画面与服务器状态一致。
6. `r1_photo` 不可提前看见。
7. 4217 不被 UI 自动泄露。
8. `LAB-42` 与 `▲ ● ■ ★` 仍按正常探索获得。
9. AI 三级提示仍正常。
10. 当前测试不能因纯画面升级失效。

达到以上标准后再进入 v4.1。

---

# 26. v4.1 实施范围

Room 2：

- 暗场景
- 通电前后视觉变化
- 电箱多状态
- 3×3 电路小游戏
- 维护说明
- 登录终端
- DATA_READ 后托盘物品
- 研究纸条
- 门禁卡
- 隐藏维护签
- Room 2 → R3

重点：

> 复用 v4.0 已建立的 SceneStateSync、动画、背包、Notebook、AI Drawer，不重新搭框架。

---

# 27. v4.2 实施范围

Room 3 + 最终 polish：

- Room 3 主场景
- 设备对应表
- 窄纸插入
- 出口刷卡
- 设备顺序小游戏
- 出口状态机
- 门开动画
- Victory
- S/A/B/C 结算
- 三房间统一音效
- 三房间统一色彩
- UI 最终统一
- 响应式处理
- Loading
- 错误状态
- 性能优化

---

# 28. 与当前仓库必须保持一致的关键事实

实施者不得根据旧版本印象自行修改这些内容：

### Room 1

- 样本玻片在 Room 1。
- 玻片用于显微镜。
- 显微镜读出 `LAB SAMPLE 42`。
- 墙钟为 `21:17`。
- 柜子密码为 `4217`。
- 柜中有保险丝。
- 柜中有批次源序 `▲ ● ■ ★`。
- `LAB-42` 是独立铭牌线索。
- Room 1 门当前是普通门闩，不需要卡。

### Room 2

- 保险丝来自 Room 1。
- 电源箱包含 3×3 旋转线路小游戏。
- 电脑只有通电后可启动。
- 终端 USER = `LAB-42`。
- PASS = `2117`。
- 电脑读取数据后出现 `research_strip` 和 `access_card`。
- Room 2 门当前也是普通门闩。
- 旧版 emergency_key 不属于当前 v3.4 主流程。

### Room 3

- research_strip 必须插入 `r3_panel`。
- access_card 用于 `exit_door`。
- 刷卡只进入 `CARD_ACCEPTED`。
- 必须再进入 `FINAL_CHECK`。
- 当前顺序小游戏实际答案逻辑是：

```text
源序 ▲ ● ■ ★
读取 3,1,4,2
得到 ■ ▲ ★ ●
对应 通风 → 冷却 → 照明 → 安全
```

- 完成顺序后才能释放门锁。
- 最终门还需要从 `UNLOCKED` 进入 `OPEN`。
- 进入 `EXIT` 后才算 `won`。

---

# 29. 开发约束

## 不修改

除非出现 v4 必须修复的真实接口缺陷，否则不要修改：

```text
backend/app/domain/*
contracts/*
游戏谜题答案
评级规则
AI读取边界
存档结构
统计规则
```

---

## 可以修改

主要修改：

```text
frontend/src/App.tsx
frontend/src/style.css
frontend/src/Assistant.tsx 的表现层
frontend/package.json
frontend/src/game/*
frontend/src/components/*
frontend/src/assets/*
```

---

# 30. Git 版本建议

```text
v4.0-room1-rusty-visual
v4.1-room2-rusty-visual
v4.2-final-rusty-visual
```

每个阶段：

1. 先运行现有测试与 build 建立基线。
2. 开发。
3. build。
4. API / 状态测试。
5. Playwright / Chrome。
6. 保存 / 恢复。
7. 手动完整路线。
8. 更新 STATUS / README。
9. 独立 commit。
10. push。

---

# 31. 最终验收标准

最终项目打开以后，用户第一眼看到的应该是：

> 一间安静、略显陈旧、处于夜间校园中的实验室。

而不是：

> React Dashboard。

玩家的主要行为应该是：

```text
看房间
↓
点击真实场景物件
↓
进入特写
↓
观察 / 尝试 / 使用道具
↓
自己组合线索
↓
设备状态发生视觉变化
↓
继续探索
```

而不是：

```text
读取卡片
↓
选择按钮
↓
系统告诉下一步
```

---

# 32. 最终项目视觉定义

> **Campus Lab Escape 是一款固定视角 2D 校园实验室密室逃脱游戏。画面采用低饱和、轻旧化、手绘感的独立游戏视觉，以夜间校园、实验设备和纸质研究记录构建自己的世界；交互结构借鉴经典 Point & Click 密室游戏的“房间总览 + 局部特写”方式，但所有房间、道具、机关、谜题、UI 与叙事均围绕本项目现有 v3.4 玩法独立设计。**

---

# 33. 实施优先级

最终执行顺序：

```text
P0
React ↔ Phaser bridge
状态同步
Room 1 主场景

P1
Room 1 完整互动
背包
笔记
AI 抽屉
保存菜单

P2
Room 2
电箱
电路
终端

P3
Room 3
终检
出口
结算

P4
统一美术
动画
音效
响应式
性能
```

**不要先画三个房间，再接游戏逻辑。**

正确方式：

```text
Room 1 画面
+
Room 1 真逻辑
+
Room 1 状态恢复
+
Room 1 体验验收
↓
再复制体系到 Room 2 / Room 3
```

这能最大限度降低返工风险。
