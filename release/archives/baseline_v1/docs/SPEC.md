# 逃离校园实验室 — 契约 v1

契约版本 `1.0.0`；基线关卡 `1.0.0`。Main 于 2026-10-01 审查批准冻结。本文件定义要求，不能当作实现或验收通过证据。依据：完整 `docs/execution-plan.md` V2.1。唯一开发责任人为用户；COURSE01、自由选题、真实模型凭据/预算及真人签署仍须实际确认。

## Intent 与边界

提供一个本地三房间网页解谜游戏。玩家探索、收集、用道具、输入密码及移动；AI 只引用玩家已知信息，提出下一步建议；后端判断真实结果。固定谜题、六工具、一次性确认、单槽存档、可复现工程证据是 MUST。联机、登录、3D、自动通关、随机地图、云部署、额外商业功能不在范围内。体验目标为一次约 10–15 分钟，未有真人试玩事实。

公共契约只含接口结构与安全标识；秘密答案和完整通关路线仅在离线 `docs/level_design.md` 及服务端规则配置中。离线文档不得被静态站点打包、HTTP 暴露、送入模型或混入可见历史。该文档可作为开发和确定性判定资料，不能作为模型输入。

## 机器契约入口

`contracts/api.schema.json`：Draft 2020-12，所有业务对象 `additionalProperties: false`；按 `$defs` 校验指定请求/响应，根定义也接受所有响应。`contracts/tools.schema.json`：六工具名称和严格参数。`contracts/tools.json`：Provider 的工具定义，适配器负责供应商包装。`contracts/routes.json`：完整路由、请求/响应定义、HTTP 状态。`contracts/build_contracts.py`：重建上述文件，无隐藏答案。

JSON 是实现契约，以下文字规定结构校验之外的事务和动态规则。禁止以 FastAPI 默认 detail 错误代替统一错误包装；任何额外字段、参数类型不符、空 code、非数字 code、长度大于 16 都是 BAD_ARGUMENT。未知工具为 INVALID_TOOL；未知对象/道具/目标 ID 通过基本字符串校验后必须动态拒绝。

## HTTP 和包装

`Content-Type: application/json`；POST body 必须为 JSON 对象。所有会话路由校验 `X-Session-Token`。只有创建响应含 token，浏览器存于 sessionStorage，不进入事件/Trace/证据/仓库。不存在会话和错误 token 同样返回 FORBIDDEN_SESSION，不泄露该会话是否存在。认证失败响应 `visible_state: null`。

成功为 `{ok:true,event_id,data}`。失败为 `{ok:false,event_id,error:{code,message},visible_state}`，认证成功后业务错误可返回当前可见投影；解析失败、认证失败及内部错误返回 null。event_id 为无秘密的追踪 ID，每个请求/失败都有。错误 message 可读但不能包含正确密码、秘密配置、token、供应商密钥或原始异常。普通 GET 的 event_id 只用于关联响应，不要求改变游戏事件序列。

| 方法及路由 | 请求 `$defs` | 成功 `$defs` | HTTP |
|---|---|---|---|
| POST /api/sessions | empty_request，即 `{}` | create_response | 201 |
| GET /api/sessions/{id}/state | 无 body | state_response | 200 |
| POST /api/sessions/{id}/actions | action_request | action_response | 200 |
| POST /api/sessions/{id}/reset | version_request | control_response | 200 |
| POST /api/sessions/{id}/save | version_request | control_response | 200 |
| POST /api/sessions/{id}/restore | version_request | control_response | 200 |
| POST /api/sessions/{id}/ai/turns | ai_turn_request | ai_turn_response | 200 |
| POST /api/sessions/{id}/proposals/{pid}/confirm | empty_request，即 `{}` | action_response | 200 |
| POST /api/sessions/{id}/proposals/{pid}/cancel | empty_request，即 `{}` | cancel_response | 200 |

工程骨架 health 路由为 `GET /api/health`，属于工程探针，不是游戏或模型工具；响应按骨架约定。

action_request 必须含 request_id、revision、generation、tool、arguments；version_request 含前三项；AI 请求再加 message。request_id 是客户端生成的无秘密 ID，1–100 位字母数字、下划线或横线；generation 为服务端 UUID；revision 为非负整数。动作、保存、重置、恢复均按 session_id/request_id 保留请求摘要。AI turn 同一 request_id 不重复调用模型或产生第二提案；其摘要包含 message 和绑定版本。

错误码与 HTTP：422 BAD_ARGUMENT/INVALID_TOOL；403 FORBIDDEN_SESSION；404 PROPOSAL_NOT_FOUND/SAVE_NOT_FOUND（仅鉴权后）；409 NOT_VISIBLE/PRECONDITION_FAILED/WRONG_CODE/ALREADY_TAKEN/GAME_FINISHED/STALE_STATE/STALE_GENERATION/REQUEST_ID_CONFLICT/PROPOSAL_EXPIRED/PROPOSAL_CANCELLED/PROPOSAL_INVALIDATED/PROPOSAL_REJECTED/INVALID_SNAPSHOT/SNAPSHOT_VERSION_MISMATCH；503 MODEL_UNAVAILABLE；504 MODEL_TIMEOUT；502 MODEL_INVALID_OUTPUT；429 AI_LIMIT_REACHED；500 INTERNAL_ERROR。有效 AI 轮次内模型失败优先返回 status=stopped 的成功包装，保留已登记线索；请求尚未开始或无法形成有效轮次时才用对应 HTTP 错误。

## 可见投影

visible_state 必须含 schema_version、level_version、session_id、revision、generation、status、room、objects、inventory、clues、exits、progress、save。schema_version 固定 `1.0.0`；room 为 `{room_id,name,description}`；status 为 playing/won；room_id 为 R1/R2/R3/EXIT。

objects 只含当前房间可见对象 `{object_id,name,kind,description,actions}`。description 是场景外观摘要，不得提前显示未发现线索正文。每个 actions 元素为 `{tool,label,arguments,requires_code}`；其 arguments 是完整工具参数，只有 submit_code 使用 `{target_id}` 模板并要求用户填 code；其余 requires_code=false。actions 是界面操作提示，不是服务端授权依据；服务器始终复验。锁住的容器仍提供 inspect/submit_code；已开的容器只提供 inspect。门可 inspect；合法道具操作由 inventory.usable_targets 提供。道具对象在可拾取时提供 inspect/take。

inventory 为已持有物品 `{item_id,name,description,usable_targets}`；usable_targets 仅列当前可见、适用目标，已开门或已安装状态不用重复提示。clues 按首次发现顺序保存 `{clue_id,object_id,title,text}`，跨房间保留，ID 唯一，恢复顺序一致。objects 可含容器刚打开后出现的物品，未打开不能出现。exits 为当前相邻目的地 `{destination_id,name,unlocked}`，可以显示锁门目的地但必须禁止直接移动。progress 只公开 power_on/check_done；不暴露答案、完整 flags、未知线索或规则条件表。save 为 null 或单槽摘要 `{schema_version,level_version,saved_at,source_revision,source_generation}`，没有 game_fields/hash/其他会话内容。

初始：R1、playing、revision=0、全新 generation、空背包/线索；objects 包含 r1_note/r1_cabinet/r1_door；R2 exit locked；power_on=false/check_done=false；save=null。房间对象及 clue IDs 的完整离线定义见 level_design。

## 六工具与探索边界

| 工具 | 参数 | 执行边界 |
|---|---|---|
| inspect | object_id | 当前可见对象；返回当前观察，必要时登记线索 |
| get_inventory | `{}` | 只读背包；observation 是可见背包文字，state.inventory 是结构化真值 |
| take | item_id | 当前可拾取物品，只入背包一次 |
| use_item | item_id,target_id | 持有物品、目标当前可见、合法配对与前置满足 |
| submit_code | target_id,code | 当前可见密码目标；数字字符串 1–16 位，精确匹配，不自动修剪/转数 |
| move | destination_id | 当前相邻已解锁房间；EXIT 还需出口检查条件 |

inspect/get_inventory 在 AI dispatcher 中称为只读工具，含义是“不推进谜题/道具/房间”。inspect 登记新已发现线索是唯一允许的知识状态副作用；第一次登记递增 revision，一次 inspect 最多一次递增，重复 inspect 无变化。r2_monitor 未通电时可 inspect 但只返回“当前无显示”，不登记线索；通电本身不自动发现屏幕线索。inspect 已开容器描述内容，不自动领取物品。模型不能直接调用 HTTP actions；四个进度工具只能生成保存提案，AI 不可绕过确认。GET state 永不登记线索。

take 未显露物品为 NOT_VISIBLE；已领取后重复 take 为 ALREADY_TAKEN，不增 revision；use_item 无物品或配对错误为 PRECONDITION_FAILED，目标不可见为 NOT_VISIBLE；错码为 WRONG_CODE，不暴露答案；合法重用已开门/已开容器/已完成检查可返回 changed=false 的成功，无道具消耗；但目标仍必须可见，CH01 已开门重用不再要求已消耗的钥匙。won 后禁止 take/use_item/submit_code/move，返回 GAME_FINISHED；允许 state/inspect/get_inventory/save/restore/reset。

## 真值、版本、收据与并发

内部可信状态最小字段为 room_id、inventory、discovered_clue_ids、flags、opened_containers、status、revision、generation，客户端永不能指定状态结果。每个成功改变玩法/知识的动作 revision+1；不变成功与失败不增；save/proposal/cancel/AI文字不增 revision。新建 revision=0；reset/restore 为当前 revision+1，generation 换新 UUID。restore 不采纳旧 revision/generation。event_id 及追加事件不得回退。

动作事务顺序：鉴权 → 校验 body/工具 → 校验当前 generation → 查 session/request_id 收据 → 相同完整请求摘要返回原 receipt + replayed=true + 当前 state；同 ID 换内容 REQUEST_ID_CONFLICT → 校验 revision → 动态规则 → 提交状态/事件/收据。请求摘要包含操作类别、revision、generation、tool、规范化 arguments；AI 摘要额外包含 message。旧 generation 即使命中旧收据也拒绝 STALE_GENERATION。失败请求同样记录不可篡改失败结果，不推进玩法；相同当前 generation 的失败重放保持原错误及当前 state。重放错误仍为错误包装，event_id 保持原失败事件 ID。两个相同版本的有效进度动作最多一个提交，另一个 STALE_STATE。

receipt 是不可变真实成功记录 `{request_id,event_id,tool,arguments,generation,revision_before,revision_after,changed,message,observation,new_clue_ids,consumed_item_ids}`；action_data 为 `{receipt,replayed,proposal,visible_state}`。手动动作 proposal=null，确认返回更新后 proposal。receipt.event_id 为原执行事件，包装 event_id 本次追踪 ID 可相同或新值，不能用包装 ID 证明再次执行。提案日志不能当成 committed 证据。failed 没有成功 receipt；失败事实保存在事件/幂等表。所有摘要仅包含该玩家已提交或可见数据，无 token/秘密规则。

控制操作 save/reset/restore 用同样版本及 request_id 语义；reset 保留会话/token及已有单槽存档，清空玩法和线索，新 generation 使旧提案失效。UI 重置需说明清空当前进度、存档仍可恢复。reset/restore 改代后旧请求重放拒绝 STALE_GENERATION，因此响应丢失时前端 GET state 后显示实际状态，不盲目用新版本重复操作。

## 单槽保存恢复

save 不修改玩法/版本，只覆盖本会话单槽并更新 visible_state.save；快照为后端构造，不接受客户端 game_fields 或任意导入。服务端私有快照包括 schema_version、level_version、session_id、game_fields、saved_at、checksum；checksum 为 UTF-8、排序键、紧凑 JSON 的 SHA-256，排除 checksum 字段。game_fields 只含玩法字段，revision/generation 不从快照恢复。存档校验归属、结构、hash、关卡版本及不变量；无存档 SAVE_NOT_FOUND，版本不同 SNAPSHOT_VERSION_MISMATCH，其他破坏 INVALID_SNAPSHOT，当前状态不被覆盖。验证事务成功后 restore 新 generation、revision+1、所有旧提案失效、事件继续追加。v1/v2 不静默迁移；回退使用独立 v1 数据目录。

## AI 与提案

AI turn 在本会话当前版本开始；只输入统一 visible_state 和可见历史，绝不读取离线解法。默认最多 3 次模型请求、5 次只读工具、1 个进度提案；单请求 20 秒、总 45 秒、输出约 1000 token；有效配置必须记录。格式纠正最多一次，不覆盖次数上限。mock 与真实 Provider 分离。真实调用须凭据及获准预算，缺少时继续 mock，不能宣称真实 AI 验收通过。

ai_turn_data 为 turn_id、answer、clue_refs、proposal、status、stop_reason、usage、visible_state。status completed/no_suggestion/stopped；完成时 stop_reason=null。clue_refs 及 proposal.clue_refs 必须是输出 state.clues 中的真实 ID；拒绝未知引用而非伪造正文。模型文本需要不宣称未执行动作成功；已发现数字可推理和引用。信息不足时说明缺口，建议查看可见对象。usage provider/model 来自真实配置；无法取得 token 为 null，不能填零假装实际用量。轮次中手动状态变化则停止/拒绝旧提案，返回当前投影。

proposal 保存 proposal_id、tool、arguments、revision、generation、expires_at、status、clue_refs、summary；只能四进度工具，绑定最后一次探索完成时的版本。服务端先做无副作用合法性预检，不允许 wrong_code 提案；但不得把正确答案加入预检错误。TTL 默认 120 秒，UTC RFC3339。confirm/cancel body 只能 `{}`，路径 pid 定位服务端参数，不能替换 code/target/item/version。confirm：事务鉴权、归属、generation、pending、未过期、revision、前置 → 一次执行 → committed 与 receipt 原子保存。相同 generation 的已 committed 重复确认返回原 receipt+当前 state，无再次消耗；generation 改变后包括已 committed 提案均拒绝 PROPOSAL_INVALIDATED。过期 EXPIRED，cancelled CANCELLED，失效 INVALIDATED，规则失败 REJECTED 对应错误码。并发确认只能一次提交。cancel pending→cancelled，不动 revision；重复 cancel cancelled 返回同一取消状态；已 committed 不能取消（PROPOSAL_REJECTED），过期/失效返回对应错误。

## 界面与证据

场景、背包、线索、AI、确认、保存/恢复/重置、通关反馈必须可见；按钮可键盘操作，宽度 1280/768/390 可用。显示 state 为唯一真值；只应用不低于当前 revision 的响应；generation 改变时清空提案和临时输入。AI 故障不清除游戏。确认显示真实 tool/arguments、摘要、期限和引用，取消无推进。Trace 记录版本、工具、合法可见输入及真实结果，明确 proposed/committed/cancelled/rejected，无秘密/token。

开发检查入口、实验72条计划行（12点×2方案×3重复，预算未定不实际调用）、评价四状态/六类校准、CH01、受控对抗、干净交接是交付要求，是否通过必须以真实输出为准。不能把本契约视为批准预算、课程审批或验收结果。

## 需求与验收追踪

| 需求 | MUST | 验收 |
|---|---|---|
| R01 | 创建重置、会话隔离 | A01,A14 |
| R02 | 六动作、三房间人工通关 | A02,A03,A04 |
| R03 | 后端唯一真值 | A04,A07 |
| R04 | 幂等、版本冲突、失败不推进 | A05,A06,A21 |
| R05 | AI白名单与可见边界 | A07,A10,A17 |
| R06 | 固定参数一次性确认、取消、期限 | A08,A09,A21,A23 |
| R07 | 真实线索引用、缺口说明 | A11,A24 |
| R08 | 单槽、归属/版本、恢复失效旧提案 | A12,A13,A23 |
| R09 | 超时、格式、循环、限额停止 | A15,A16 |
| R10 | 密钥只在服务端，无公开泄漏 | A10,A18 |
| R11 | 版本/输入/工具/结果 Trace | A19,A26 |
| R12 | 桌面/窄屏、加载失败通关反馈 | A02,A20 |
| R13 | 开发Harness与运行Harness | A07,A08,A09,A22 |
| R14 | 可比上下文实验、逐次输入失败用量 | A24 |
| R15 | 评价独立入口、四状态、引用、六校准 | A25 |
| R16 | CH01、Finding、修复与独立复测 | A17,A21,A23,A27 |
| R17 | 干净安装、重启恢复、版本回退、README | A12,A28 |
| R18 | 实际人机决定、个人说明、课程适用 | A26 + O1/O7签署、COURSE01（不能仅凭 A26 判通过） |

## 确定性反例（验证设计，尚未执行）

N01：未开柜 take access_card → NOT_VISIBLE，背包/revision 不变。N02：错误 code → WRONG_CODE，不显示正确值，不开柜/抽屉。N03：无卡 use_item 到 r1_door → PRECONDITION_FAILED，不开门。N04：未供电 inspect r2_monitor → 成功“当前无显示”，无屏幕 clue，无 revision 变化。N05：A token 请求 B 全部会话资源 → FORBIDDEN_SESSION/null state。N06：同 request_id 换参数 → REQUEST_ID_CONFLICT；原状态不重复执行。N07：旧 revision 或 generation → STALE_STATE/STALE_GENERATION。N08：confirm body 添 code → BAD_ARGUMENT，提案无推进。N09：restore 后旧 proposal → PROPOSAL_INVALIDATED。N10：任意 extra flags/won 或未知 tool → BAD_ARGUMENT/INVALID_TOOL，无客户端指定结果。N11：并发同 pid → 一条 committed receipt，无第二次进展。N12：v1 快照在 v2 restore → SNAPSHOT_VERSION_MISMATCH，当前状态不覆盖。
