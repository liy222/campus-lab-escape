# 游戏升级路线与交付门槛

本文跟踪 `docs/upgrade-plan.md` 中已接受的 v3.0–v4.2 范围。计划是设计基线，不是执行或验收证据。v4.2 三房间视觉与最终界面及 v4.2-handpainted 手绘素材增量均已按各自联合 QA 证据接受并 SOURCE STOP；规则关卡仍为3.4.0、Schema 1.4.0，原有 AI、启动器和多时刻本地存档保持。此前 v3.4、v3.3、v4.0、v4.1 提交和标签均已推送核实；v4.2 commit `74f6272b9204f352a6b598d3bd4273452f8184be` 与 tag `v4.2-final-rusty-visual` 已推送核实，GitHub 作者与提交者均为 `liy222`。`CH01_v2` 是历史冻结基线。旧版工程检查、实验与评价器结论不会自动扩展到本升级路线。

| 版本 | 主要范围 | 当前状态 |
|---|---|---|
| v3.0 | 降低信息暴露；统一观察、互动、使用物品入口 | 独立 QA 通过；已推送 commit `1499610`，tag `v3.0-gameplay-information` |
| v3.1 | 多状态物体及对应视觉状态要求 | 独立 QA 通过；commit `cfab6616c288fc1d5a3b41ae118911a13e9ad321` 与 tag `v3.1-object-state` 已推送 |
| v3.2 | 重设计三房间谜题网络并完成房间灰盒布局 | 独立 API QA 通过（97 passed、257 子项、exit 0）；commit `519c8d0d542fcfedd4bfaaaf8b81e68b00d05925` 与 tag `v3.2-puzzle-redesign` 已推送 |
| v3.3 | 线路连接、顺序操作两类小游戏及可操作灰盒 | 独立 QA 按联合 API 运行与定向复验、同候选 build/browser 结果接受；SOURCE STOP；commit/tag 已推送 |
| v3.4 | 跨房间线索、AI 三级提示、结算与完整灰盒通关 | 联合 QA 接受并已推送；多时刻存档增量也已联合 QA 接受并推送 |
| v4.0 | 引入 Phaser，完成 Room 1 固定视角画面 | 联合 QA 接受并 SOURCE STOP；commit `1047e293ade70e446c9c76be0a0d751f3e3ad81a` 与 tag `v4.0-room1-rusty-visual` 已推送核实 |
| v4.1 | 完成 Room 2 正式画面 | 联合 QA 接受并 SOURCE STOP；commit `161d3e6f25406d44eb55c48c295b86c7289d8f2c` 与 tag `v4.1-room2-rusty-visual` 已推送核实 |
| v4.2 | 完成 Room 3、统一 UI、音效、动画与最终优化 | 联合 QA 接受并 SOURCE STOP；commit `74f6272b9204f352a6b598d3bd4273452f8184be` 与 tag `v4.2-final-rusty-visual` 已推送核实；手绘素材增量另见下文 |

## v3.0 已完成范围

Main 确认 v3.0 独立工程验证通过：82 pytest、220 个子项、前端 build exit 0；Chrome 全三房间 EXIT 流程通过；8 种错误目标尝试后状态、修订号和背包均不变；R2 存档保存/恢复、刷新继续及 1280/375 视口无溢出均通过；4 个源码文件前后 hash 匹配。后端关卡级别 2.0 与 Schema 1.0 保持，旧存档恢复路径已核对。

证据：[`formal run summary`](../evidence/upgrade/v3.0/qa/20261006T093937475Z-formal/run-summary.json)、[`browser run`](../evidence/upgrade/v3.0/qa/20261006T094303859Z-browser/run.json)。这些是工程自动化覆盖，不是人类试玩，也没有实际验证真人20–30分钟通关体验。Main 已推送 commit `1499610` 并创建 tag `v3.0-gameplay-information`；此处仅记录已核实的短 SHA，不推断完整 SHA。

## v3.1 独立 QA 通过

最终修复候选的全套 API QA exit 0：89 passed（既有82项与新增7项）、235个子项通过；13个候选源码哈希与冻结清单匹配。验收覆盖39步三房间路线、四条设备状态链、各设备推进阶段的 save/reset/restore/Store reopen、严格 `interact` 参数与损坏快照拒绝。损坏快照缺少已观察对象或线索时被拒绝，session 与存档槽未被覆盖。QA 结果和范围见 [`最终摘要`](../evidence/upgrade/v3.1/qa/result.json) 与 [`独立报告`](../review/findings/upgrade-v31.md)。

构建与 Chrome 浏览器记录来自后端存档不变量修复前的候选，不能标作修复后源码的浏览器复验。浏览器记录覆盖三房间通关、保存/恢复、刷新与 OS 后端重启、375px 布局、legacy 入口与存储隔离；具体候选 epoch 见摘要。v3.1 前端 owner build exit 0及源码哈希见 [`前端记录`](../evidence/upgrade/v3.1/frontend.json)。最终修复后针对 API 路线与各设备阶段重新运行了全套 API QA。

本阶段使用合成 AI fixture，没有真实 provider/网络调用；没有真人试玩或20–30分钟体验验收。legacy 浏览器检查使用 QA 创建的 level-2 存档，不读取历史敏感数据库。v3.1 使用独立 `game-v3.1.sqlite` 与 `campus-lab-session-upgrade-v3.1` 浏览器存储；同代码 legacy 继续使用 `game-v2.sqlite` 与 `campus-lab-session-v1`。本 QA 不迁移或重置既有数据。v3.1 commit `cfab6616c288fc1d5a3b41ae118911a13e9ad321` 与 tag `v3.1-object-state` 已推送。

## 每阶段交付门槛

每个版本完成时都要实际运行后端测试与前端构建，从主路线实际走通游戏，并核对保存、恢复、刷新后的状态同步。报告应绑定本阶段真实源码和检查结果；只有候选稳定后再做独立 QA。每阶段还要记录旧存档策略，按该策略实际验证既有存档兼容或迁移，再由 Main 使用用户指定 Git 身份提交并推送该版本。未完成这些步骤时，不得将计划状态改写为通过。

v3.1 使用关卡级别 3.1、Schema 1.1 与独立数据库/浏览器 session namespace；历史 v2 数据继续由同代码 legacy 模式读取，不自动迁移。后续若改变状态或存档结构，必须先明确兼容、迁移或不兼容处理规则，再按规则验证既有数据，不删除或重置现存数据。

## v3.2 独立 QA 通过

v3.2 使用关卡级别 3.2、Schema 1.2，默认独立 `game-v3.2.sqlite` 与 v3.2 浏览器 session namespace；显式 legacy 与 v3.1 模式及各自数据空间保留，不自动迁移。正式独立 API 复验在修复后候选上 exit 0：97 passed、257 个子项通过、1 个弃用警告，覆盖原有89项和新增8个测试方法。覆盖46步三房间路线与46次阶段保存/Store重开/恢复、错误目标无副作用、跨版本快照拒绝、AI读取边界等；首轮发现的既有线索内容伪造问题及另11类伪造读取均由完整 API 复验检查，全部通过。结果及证据见 [`v3.2 QA 摘要`](../evidence/upgrade/v3.2/qa/result.json) 与 [`独立报告`](../review/findings/upgrade-v32.md)。

Chrome 61项检查和前端 build exit 0来自原候选，来源与结果被保留复用；修复仅涉及 AI runtime，修复后没有重复运行浏览器或 build。根目录启动 CMD 做了字节/配置检查，但没有实际启动。测试使用合成 AI callback/provider，没有付费或真实模型调用；没有真人试玩或20–30分钟通关时长验收。现有 Starlette TestClient/httpx 弃用警告仍存在。v3.2 commit `519c8d0d542fcfedd4bfaaaf8b81e68b00d05925` 与 tag `v3.2-puzzle-redesign` 已推送。

## v3.3 独立 QA：联合证据接受

v3.3 使用关卡3.3.0、Schema 1.3.0，默认独立 `game-v3.3.sqlite` 与 `campus-lab-session-upgrade-v3.3` 浏览器 session namespace；显式 v3.2、v3.1 与 legacy 模式及各自数据库/session 保留，不自动迁移。三种新手动操作是旋转线路模块、提交线路和提交四设备顺序；AI 原有工具保持不变。

线路灰盒根据服务器公开的3×3模块形状和旋转状态绘制。玩家点击模块顺时针旋转90°，方向端口、电源和主系统标识帮助阅读布局；只有点击“提交线路”才由服务器验证连通性。前端不计算解法；局部线路状态由服务端持久化。顺序面板以不同于 Room 1 源符号顺序的设备列表呈现，玩家可逐项加入草稿、重复选择、清空或提交；只有服务器确认后才推进进度。草稿仅留在当前页面，刷新、重置、恢复存档、切换房间或 generation 时清空。

API 证据是两个 epoch：首轮全套运行 exit 1，105 passed、291 个子项通过、1 个 QA 尾部预期错误；唯一失败断言误以为普通 `interact r3_panel` 应返回 200，服务器按设计返回 409 并阻止小游戏旁路。随后只修正该新方法的 QA 预期并定向复验，exit 0，1 passed、3 个子项通过。旧 97 项和新增 9 个 API 方法由首轮全套与定向复验联合覆盖；没有重跑全套 exit 0，也没有宣称 106 passed。两次运行均有既有 TestClient/httpx 弃用警告。

全程 27 个产品候选文件 before/after 匹配。Build exit 0，Chrome exit 0、102 项摘要检查、issues 为空，6 张截图已目视检查；Chrome 与 build 均绑定该候选且未重跑。浏览器覆盖手动线路旋转/服务器提交、线路局部存档保存恢复与进程重启、四设备顺序及错误草稿、恢复/刷新/换房间清除草稿、主电闸交互、终检胜利、375px 布局与旧版本 session 隔离。线路和顺序截图来自桌面；375px 小游戏布局由 DOM 几何检查覆盖。

根目录 launcher 首轮检查因 QA 错误期待不存在的命令行 flag 而 exit 1；按实际 `GAMEPLAY_VERSION=upgrade`、v3.3 数据库与 `--provider mock` 配置重新检查 exit 0。没有实际启动根目录 CMD。QA 使用合成 provider，没有真实模型质量或真人20–30分钟通关时长验收；旧版本仅用新建 session/save slot 检查，没有读取历史敏感数据库。详细计数、命令、候选绑定与限制见 [`v3.3 QA 结果`](../evidence/upgrade/v3.3/qa/result.json) 和 [`独立报告`](../review/findings/upgrade-v33.md)。owner build、launcher 和文档记录分别见 [`前端记录`](../evidence/upgrade/v3.3/frontend.json)、[`Delivery 记录`](../evidence/upgrade/v3.3/delivery.json) 与 [`文档记录`](../evidence/upgrade/v3.3/docs.json)。本阶段没有加入 Phaser、最终美术或付费 provider 调用。v3.3 commit `58587cf9458920fef435e8cb5d7638b1e318c19b` 和 tag `v3.3-mini-games` 已推送。

## v3.4 独立 QA：联合证据接受

v3.4 使用关卡3.4.0、Schema 1.4.0、独立 `game-v3.4.sqlite` 与 `campus-lab-session-upgrade-v3.4`；v3.3/v3.2/v3.1/legacy 各自数据空间保留且不自动迁移。三级提示选择仅本地生效，点击“获取提示”才请求；真实模式只向模型服务发符合条件的提示主题名称与已发现线索 ID，不发玩家问句、对话历史或线索全文，旧版助手和 API Key 内存清除行为保持不变。服务器统计/结算涵盖10条线索、最多2条隐藏发现、提示、失误、用时与 S/A/B/C；用时包括离线并在胜利冻结，存档恢复回滚统计，重置新计时但保留存档槽；评级不影响通关，S/A/B 阈值分别为线索≥9且提示≤1/失误≤2、线索≥7且提示≤3/失误≤5、提示≤8，其余为 C。正式 API 联合覆盖为：首轮全套 exit 1，118个方法通过、315个子项通过、1个子项失败（新并发用例误期望 reservation 中相同请求返回409，实际返回503 `MODEL_UNAVAILABLE`）；仅该新方法修正预期后的定向复验 exit 0，1个方法、3个子项通过。没有第二次全套 exit 0，也不重复相加子项。冻结候选38条产品/合同/规格/launcher路径哈希一致；build exit 0，Chrome exit 0、132项、issues为空，6张截图已查看；launcher 字节/配置检查 exit 0，但根目录 CMD 未实际启动。结果、命令与边界见 [`v3.4 QA 结果`](../evidence/upgrade/v3.4/qa/result.json) 和 [`独立报告`](../review/findings/upgrade-v34.md)。本次使用 mock/stub、付费调用0；没有真实模型质量/密钥验证、真人20–30分钟时长证明或历史敏感存档迁移验收，仍有既有 Starlette/httpx 弃用警告。灰盒 QA 阶段曾按用户指示暂缓画面升级；用户随后提供详细计划并授权 v4.0，Room 1 视觉阶段现已完成联合 QA。v3.4 commit `49a2f925a78055552781685e79ee96496bb9bdd6` 与 tag `v3.4-graybox-complete` 已推送并核实，GitHub 作者与提交者均为 `liy222`。

## v3.4 多时刻存档增量：联合验收通过

在同一已认证本地游戏中，每次“保存新存档”都会新增一个独立记录；名称可选、最多40字，留空由服务端按时间命名。列表按保存时间倒序显示名称、时间、房间、进行/通关状态与线索数；“读取”经确认后替换当前进度，服务端验证存档并切换 generation。reset 保留全部存档，restore/reset/save/同步后重新读取列表；异步列表响应按当前游戏、generation 和 revision 检查，避免过期结果覆盖界面。新表追加保存，不删除、不覆盖既有新存档；旧版单槽以“旧版单槽”条目出现，房间/状态/线索数量显示为未知，不解析旧私有快照；旧单槽控件和旧 API 保留，单槽保存只替换那一份旧记录。多存档接口为 `GET /api/sessions/{id}/saves`、`POST /api/sessions/{id}/saves` 与 `POST /api/sessions/{id}/saves/{save_id}/restore`；游戏仍使用现有 sessionStorage 会话和本地 DB，不提供账号、云端或跨浏览器同步，新游戏会创建另一份游戏存档列表。冻结41个产品/兼容路径不变。正式全套 API 首轮 exit 1：126方法与336子项通过，1方法和1子项因新增 QA 预期错误失败（恢复后旧提案应失效；已完成失败请求应重放原错误）。只修正这两处新测试预期，定向复验 exit 0：2方法、9子项通过，含另用新请求标识验证旧 generation 被拒绝；这是联合覆盖，没有第二次完整全绿运行，重叠子项不相加。最终 build exit 0，真实 Chrome exit 0、149检查、issues为空，覆盖早期/线路中期/通关三份命名存档、指定恢复与取消、刷新、进程重启、旧槽、375px、转义名称及旧版本入口；11张截图经 QA 查看，Main另查看存档列表和确认图。测试仅 mock/stub，付费0；本次自有服务已退出，保留用户既有环境；仍有既有 Starlette/httpx 弃用警告。根CMD未交互启动，不证明真人游玩时长。证据见 [`Main验收`](../evidence/integration/multiple-saves/accepted.json)、[`独立报告`](../review/findings/multiple-saves.md) 和 [`Backend owner记录`](../evidence/integration/multiple-saves/backend.json)。

增量 commit `8e491d7c4b4972cb4a3972627fde3a5fc98c28ee` 与 tag `v3.4-multiple-saves` 已推送并核实；GitHub 作者与提交者均为 `liy222`。关卡/Schema 仍为3.4.0/1.4.0，未进入画面阶段。

## v4.0 Room 1 视觉阶段：联合 QA 接受

在 v4.0 阶段，Room 1 首次使用 Phaser 4.2.1 Canvas 与原创 SVG，采用固定视角点选和局部特写；四槽背包、线索笔记、AI 助手与存档菜单以抽屉/游戏内面板呈现。当时只更新 Room 1，Room 2、Room 3 仍为可玩的灰盒回退画面。其联合 QA 范围与限制见 [`v4.0 验收记录`](../evidence/upgrade/v4.0/accepted.json) 和 [`独立 QA 报告`](../evidence/upgrade/v4.0/qa/result.json)。v4.0 commit `1047e293ade70e446c9c76be0a0d751f3e3ad81a` 与 tag `v4.0-room1-rusty-visual` 已推送并核实。

联合 QA 复用了历史完整 API 基线127个方法/337个子项 exit 0；初始候选定向 API 6个方法/3个子项 exit 0、build exit 0、完整 Chrome 206项 exit 0。修正候选的 build exit 0 与窄范围 Chrome 112项 exit 0，检查 CSS 和3个 SVG、26项布局记录及31项像素记录。修正候选没有重跑完整三房间路线或完整 API 套件，故运行计数不相加，也不代表修后完整路线再次通过。85项修正候选哈希匹配；相对初始 v4.0 候选仅 CSS 与3个 SVG 发生变化；付费调用0。

仍有既有 Starlette/httpx 弃用警告；根目录启动 CMD 未交互启动；受控缺失素材失败未覆盖；没有真实密钥、付费模型质量或真人试玩验收。具体 v4.0 限制见对应验收记录。

## v4.1 Room 2 视觉阶段：联合 QA 接受

Room 1 与 Room 2 现使用 Phaser 4.2.1 Canvas、原创 SVG、固定视角点选和局部特写；Room 2 加入暗/亮场景、电源箱多状态与3×3线路面板、终端状态、维护说明、数据托盘物品及普通门闩。服务器状态仍驱动画面，不改变关卡规则。规则关卡、API/Schema、AI、多时刻本地存档、启动器和 Room 1 原有26个 SVG 保持不变；R3/出口仍为可玩的灰盒。

正式 API 定向覆盖6个方法、3个子项，exit 0（11.72秒，1项既有弃用警告）；前端 build exit 0。Chrome exit 0、339项检查、issues为空，包含完整三房间路线、5份存档与旧单槽、刷新/进程重启、R1/R2触屏与键盘、35项像素记录和21项 R2 状态/布局记录。初始两次 Chrome 运行分别为204与278项、exit 1，原因是新 QA 状态观察器在刷新/新触屏上下文中丢失；只修正新 QA runner 的观察器注册，123项产品候选没有修改，最终覆盖不把重复计数相加。候选及272件 QA 产物哈希一致，付费调用0。

仍有 Vite chunk 大小警告；加载拆分、缺失素材故障处理和音效 polish 留待 v4.2。根目录启动 CMD 未交互启动；未验证真人通关时长、音效质量或付费模型质量。完整命令、失败尝试和限制见 [`v4.1 验收记录`](../evidence/upgrade/v4.1/accepted.json) 与 [`独立 QA 报告`](../evidence/upgrade/v4.1/qa/result.json)。v4.1 commit `161d3e6f25406d44eb55c48c295b86c7289d8f2c` 与 tag `v4.1-room2-rusty-visual` 已推送核实；该阶段 SOURCE STOP。

## v4.2 三房间视觉与最终界面：联合 QA 接受

Room 1、Room 2 与 Room 3 均使用 Phaser 4.2.1 Canvas、原创 SVG、固定视角点选和局部特写。Room 3 呈现设备对应表、研究纸条插入、终检顺序面板和五态出口；设备文本与玩家草稿由公开状态实时绘制，服务端负责验证。通关页显示服务器结算统计与 S/A/B/C 评级。设置提供静音与减少动画；初始画面优先加载当前场景，游戏输入会在场景加载或缺失素材时被阻断，重试从当前服务器快照恢复。关卡仍为3.4.0、Schema/API仍为1.4.0；AI、启动器和多时刻存档行为保持。

完整 API 套件一次通过：127个方法、337个子项、295.14秒、exit 0，含1项既有 Starlette/httpx 弃用警告。前端 build exit 0；主 bundle 294.66 kB（gzip 91.24 kB），Phaser bundle 1,388.18 kB（gzip 368.11 kB），Vite 的大 chunk 警告仍存在。Chrome 覆盖由多个保留 epoch 和必要定向补完联合组成：R1/R2前段290项、R2后段195项、R3到胜利245项，最终 finish epoch 283项 exit 0/issues为空；六个失败的 runner adapter epoch 均留档，最终证据不是单轮完整全绿运行，重复检查不相加。Main 接受时152个源码与238件 QA 证据均与冻结候选哈希匹配，正式 QA 没有产品修复，付费调用0。

联合覆盖包括三房间Canvas路线、R3公开顺序草稿与服务端验证、五种出口状态与阻断状态、服务器胜利统计、存档/恢复/重载/重启、移动触屏与键盘、静音/减少动画、缺失素材阻断重试和生产环境按需加载。限制包括：模块导入故障注入未覆盖；根目录 CMD 未交互启动；没有真人音效质量或通关时长、真实 provider 质量或历史敏感数据库访问验证。完整命令、失败 epoch、范围与限制见 [`v4.2 验收记录`](../evidence/upgrade/v4.2/accepted.json) 与 [`独立 QA 报告`](../evidence/upgrade/v4.2/qa/result.json)。v4.2 commit `74f6272b9204f352a6b598d3bd4273452f8184be` 与 tag `v4.2-final-rusty-visual` 已推送核实；当前阶段 SOURCE STOP。

## Stage UI 版式修正：联合 QA 接受

用户希望游戏图形画面周围的界面融入画面。修正后，桌面 HUD、背包和操作控件叠在实际 Canvas 画框内，登录表单位于终端的物理屏幕区域；窄屏的阅读/表单可作为场景内面板展开。默认视觉入口不渲染旧网页外壳，legacy 入口仍保留且与视觉入口互斥。此处记录的是版式调整，不代表曾复现旧灰盒与新场景重复显示。关卡规则、API、AI、多时刻存档和84项原创 SVG 资产未变。

联合 QA 接受最终152个源码候选；四个发生产品变更的候选各有一次 build exit 0。浏览器证据保留7个失败 epoch，另有最终 `end` 87项 exit 0 与 `feedback` 63项 exit 0/issues为空；跨候选结果不累加，也不是单轮完整全绿。已关闭三个发现：恢复确认对话框按钮高度、移动背包按钮尺寸、横屏反馈提示与 HUD 重叠。没有新跑完整 API 套件，付费调用0。范围、截图、失败尝试与限制见 [`stage-ui 验收记录`](../evidence/integration/stage-ui/accepted.json)、[`stage-ui QA 结果`](../evidence/integration/stage-ui/qa/result.json) 和 [`独立报告`](../review/findings/stage-ui.md)。修正 commit `68693a5fc36b16e21b9323e89145ca3195294499` 与 tag `v4.2-stage-ui` 已推送核实，作者与提交者均为 `liy222`；已推送的 `v4.2-final-rusty-visual` 历史标签不改写。

## Closeup 输入隔离与 Room 3 早期面板：联合 QA 接受

特写切换现在销毁旧交互区域，并校验输入仍属于当前热点；特写背景本身不可点击，柜体和托盘中的合法子物品仍可点选。Room 3 在 research_strip 插入后即显示四台设备图形并允许编辑本地草稿，最终提交仍要求服务端处于 `FINAL_CHECK`。v3.3 的旧投影与现有存档行为保持兼容。重启服务并刷新页面即可使用，现有存档无需重开。

定向 API 8项 exit 0，前端 build exit 0。浏览器联合覆盖了首轮 R1 项和最终 R2/R3 remaining 68项 exit 0；两次新 adapter 失败保留在记录中。结果跨范围联合，不表示单次完整全绿路线；没有重复全套 API，也没有付费调用。EXIT 截图恰逢房间到达过渡而偏暗，功能结算 DOM 通过，先前验收的清晰胜利画面未变。详细命令、截图与限制见 [`closeup-panel 验收记录`](../evidence/integration/closeup-panel/accepted.json)、[`QA 结果`](../evidence/integration/closeup-panel/qa/result.json) 和 [`独立报告`](../review/findings/closeup-panel.md)。修正 commit `c76e77ec9129f32606bb5dee225621cae154427d` 与标签 `v4.2-closeup-panel` 已推送核实，GitHub 作者与提交者均为 `liy222`；stage-ui 的既有 commit/tag 历史保持不变。

## v4.2-handpainted 手绘状态素材接入：联合 QA 接受

运行画面现使用80张手绘状态物件与特写图、5张净房间背景；PNG 位于 `frontend/public/art-handpainted/`，尺寸与可见包围盒元数据位于 `frontend/src/assets/painted-metadata.json`。4张复用全景未复制，`r2_light_overlay_on` 是完整场景研究图，不是透明灯光层。既有84项 SVG 保留；关卡规则3.4.0、API/Schema 1.4.0、AI、启动器和多时刻本地存档未改，现有同版本存档继续使用。

冻结候选 SHA-256 为 `e7341a6d778c0af4295c791946ec92633347287e1ae4a4d8813af3c58ab39f81`：242个源码项、389个不可变项、8个 QA 脚本和84件 QA 证据均与 Main 核对一致。85张 PNG 静态检查87项 exit 0；独立前端 build 一次，52个模块、2.98秒、exit 0，仍有既有 Phaser 大包警告。浏览器联合证据保留首轮201条记录 exit 1：R1/R2与早期 R3 CARD_ACCEPTED 实际 UI 检查后，QA 选中物品适配器把服务端409误判为应返回200；产品未修复。之后仅补剩余范围：101条 exit 0、issues为空，覆盖 fixture 准备下的 R3 FINAL_CHECK/PASS/UNLOCKED/OPEN/EXIT、终局存档与胜利；另有75条 exit 0 的已结算桌面胜利展示检查。联合覆盖还包括 PNG 故障重试、按需加载、特写隔离、线索读取、鼠标/触屏/键盘、响应式热点、存档选择、刷新及一次后端进程重启。各 epoch 记录数不相加，不能表述为一次完整浏览器全绿。

QA 在新建私有会话与数据库上运行，没有访问历史用户数据库或凭据；未重跑完整127项后端套件，复用既有冻结后端证据及窄范围 API 接受记录。没有交互启动根目录 CMD、OS 重启、付费调用或真人通关时长验收。桌面1280与移动375×812/812×375为代表性视口；当前房间会预加载本房间状态/特写图，首次欢迎页按需加载不构成加载性能认证。保留的非阻断视觉细节：R3墙面导管与控制台导管略有偏移，钟面纸张区域可见纹理接缝。完整范围与证据见 [`Main 验收`](../evidence/integration/handpainted/accepted.json)、[`独立 QA 结果`](../evidence/integration/handpainted/qa/result.json)、[`素材交付`](../evidence/integration/handpainted/assets/report.json)。QA 付费调用0。正常同步后计划使用 `v4.2-handpainted` 标签；同步核实前不视为已推送。

## 阶段边界

v4.2 三房间视觉交付已按联合证据接受并 SOURCE STOP，commit `74f6272b9204f352a6b598d3bd4273452f8184be` 与 tag `v4.2-final-rusty-visual` 已推送核实。其后的 stage-ui 版式修正已验收，修正 commit `68693a5fc36b16e21b9323e89145ca3195294499` 与 tag `v4.2-stage-ui` 已推送核实。每阶段只交付计划内所需变更，不为升级路线发起付费实验。既有双击启动、手动 AI 模式与 API Key 说明继续有效；QA 未进行付费模型调用、真人音效质量或真人通关时长验收。
