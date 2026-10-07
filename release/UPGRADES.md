# 游戏升级路线与交付门槛

本文跟踪 `docs/upgrade-plan.md` 中已接受的 v3.0–v4.2 范围。计划是设计基线，不是执行或验收证据。本地当前工作版本为 v3.2（关卡3.2.0、Schema 1.2.0），独立 API QA 已通过；Main 正常同步收尾，v3.2 tag 待登记。`CH01_v2` 是历史冻结基线。旧版工程检查、实验与评价器结论不会自动扩展到本升级路线。

| 版本 | 主要范围 | 当前状态 |
|---|---|---|
| v3.0 | 降低信息暴露；统一观察、互动、使用物品入口 | 独立 QA 通过；已推送 commit `1499610`，tag `v3.0-gameplay-information` |
| v3.1 | 多状态物体及对应视觉状态要求 | 独立 QA 通过；commit `cfab6616c288fc1d5a3b41ae118911a13e9ad321` 与 tag `v3.1-object-state` 已推送 |
| v3.2 | 重设计三房间谜题网络并完成房间灰盒布局 | 独立 API QA 通过（97 passed、257 子项、exit 0）；Main 正常同步收尾，tag 待登记 |
| v3.3 | 线路连接、顺序操作两类小游戏及可操作灰盒 | 未开始 |
| v3.4 | 跨房间线索、AI 三级提示、结算与完整灰盒通关 | 未开始 |
| v4.0 | 引入 Phaser，完成 Room 1 正式画面 | 未开始；须等 v3.4 灰盒通过 |
| v4.1 | 完成 Room 2 正式画面 | 未开始 |
| v4.2 | 完成 Room 3、统一 UI、音效、动画与最终优化 | 未开始 |

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

Chrome 61项检查和前端 build exit 0来自原候选，来源与结果被保留复用；修复仅涉及 AI runtime，修复后没有重复运行浏览器或 build。根目录启动 CMD 做了字节/配置检查，但没有实际启动。测试使用合成 AI callback/provider，没有付费或真实模型调用；没有真人试玩或20–30分钟通关时长验收。现有 Starlette TestClient/httpx 弃用警告仍存在。v3.2 tag 由 Main 按正常同步流程登记；本文件不预填 commit SHA。

## 阶段边界

v3.0–v3.4 完成灰盒并通过完整路线前，不引入 Phaser，也不制作最终美术。每阶段只交付计划内所需变更，避免把大量历史快照复制进归档；不为升级路线发起付费实验。既有双击启动、手动 AI 模式与 API Key 说明继续有效，但不构成新版玩法验收。
