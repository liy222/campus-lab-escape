# 逃离校园实验室 — 契约 1.0.0 / CH01 关卡 v2

契约版本 `1.0.0`；基线关卡 `1.0.0`，CH01 目标关卡 `2.0.0`。Main 于 2026-10-01 审查批准冻结基线；2026-10-05 的 T28 工程派发批准本次有限变更，来源与验收见下文 CH01 冻结卡。本文件定义要求，不能当作实现或验收通过证据。依据：完整 `docs/execution-plan.md` V2.1。唯一开发责任人为用户；用户于 2026-10-02 明确课程确认“不用管这个”（Main 记录在 `DECISIONS.md`），课程批准/真人签署均不推定且不阻塞工程工作。真实付费调用仍须凭据及获准预算。

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

take 未显露物品为 NOT_VISIBLE；已领取后重复 take 为 ALREADY_TAKEN，不增 revision；CH01 钥匙消耗后仍视为已领取，不能从抽屉重拾或重新生成。use_item 无物品或配对错误为 PRECONDITION_FAILED，目标不可见为 NOT_VISIBLE；错码为 WRONG_CODE，不暴露答案；合法重用已开门/已开容器/已完成检查可返回 changed=false 的成功，无道具消耗；但目标仍必须可见，CH01 已开门重用不再要求已消耗的钥匙。won 后禁止 take/use_item/submit_code/move，返回 GAME_FINISHED；允许 state/inspect/get_inventory/save/restore/reset。

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

## CH01 冻结卡：首次解锁 R3 消耗应急钥匙

任务 `T28`；冻结日期 `2026-10-05`；状态：工程规格冻结，T29 实现/T30 独立 QA 尚未执行。唯一人类开发者为用户；没有教师或真人签署事实。Main 负责将此冻结卡登记到 `review/change_CH01.md`，本节是 Spec 的设计交接。

### 版本与批准来源

- baseline_product_commit：`7821af4efe0613c20a80ea164c1dab1c0f288bab`（Main 派发登记，Spec 未运行 Git 验证）。
- baseline_level_version：`1.0.0`；target_level_version：`2.0.0`。
- API/contract/tool/schema：均保持 `1.0.0`，六工具、九路由、公开字段不变。
- Main 登记的冻结源码：`release/archives/baseline_v1/`，101 原始源码文件；索引 `evidence/integration/E1-source-archive-20261005.json`，raw SHA256 `0dab9b9e213a3631a7630eb59cd0a27d8e44c74321891463ed7d71d599d285a6`。本次只读核对索引哈希；archive 不修改。
- engineering_approval：Main 于本会话 T28 派发明确批准该有限工程变更，依据用户已授权完整任务、`docs/execution-plan.md` T28/第21节；Main 的 `DECISIONS.md` 记录用户于 2026-10-02 说课程确认“不用管这个”。不把工程派发推定为教师批准或玩家试玩接受。
- teacher_approval：`null`；human_signoff：`null`。不阻塞工程实施，不宣称正式课程 Change 或真人互审。
- E1 前置结果引用独立 `review/findings/T25-independent-formal-20261005.md`：Main 派发报告 1829 检查 exit 0；22 完成、1 超时、49 not_called。停止/失败保留，不宣称摘要 B 优越；本次不重写或重新调用 E1。

理由：以一个已有道具的生命周期变化验证规则、原子提交、可见投影、保存恢复和确认边界。范围只有应急钥匙首次开 R3 时消费一次；不扩地图、账号或重构。

### 规则、影响与不变量

首次成功 `use_item {item_id:emergency_key,target_id:r2_door}` 必须在同一次可信状态转换与提交中移除钥匙、永久解锁 R3 门，receipt 的 `consumed_item_ids=[emergency_key]`、`changed=true`，revision 只增加一次。首次开门仍要求玩家在 R2、目标可见、已供电且持钥匙；失败无消费、无解锁、无版本推进。基线 v1 用后保留钥匙的规则只在独立 v1 源码/数据目录中保留。

同 request_id 重放或同 committed proposal 再 confirm 返回不可变原 receipt（包括原消费列表）及当前 visible_state；`replayed=true` 不代表第二次消费。新 request_id 合法重用已解锁门返回不变成功、`consumed_item_ids=[]`、`changed=false`，不需背包仍有钥匙。并发首次动作/confirm 只能提交一次消费，沿用既有版本冲突/确认规则。R2↔R3 往返始终畅通，无需重用钥匙。

v2 的 r3_unlocked 同时证明钥匙已领取/消耗；要求 power_on、抽屉已开且背包无钥匙。钥匙不再显露/可拾取，抽屉观察不得声称仍有可领取钥匙；HTTP、背包工具和 AI 共用可见真值。消费事实只由真实 committed receipt/公开反馈说明，模型不能把提案当成已消费。visible_state、新快照/save 摘要 level=2.0.0；既有 schema 已允许两关卡版本，不意味着跨版本快照可恢复。

v2 开门前/后同版本保存恢复均可用；恢复新 generation，旧提案/请求不能执行。显式恢复开门前玩法允许新 generation 再首次开门，这是恢复事实，不能误判为同一状态重放消费。v1 快照在 v2 拒绝 SNAPSHOT_VERSION_MISMATCH，当前玩法/版本不覆盖；同版本损坏不变量 INVALID_SNAPSHOT。回退使用独立 v1 DB，无静默迁移，不将 v2 DB 向 v1 输入。

只读影响检查：`backend/app/domain/rules.py` 的 LEVEL_VERSION、use_item 消费、visible_objects、take 已领取判定、inspect 容器描述、validate_invariants 是必要变更点；`backend/app/storage/sqlite.py` 已有版本拒绝入口，需要 v2 边界局部验证；AI/前端需要核对消费投影与结果说明。公共 JSON schema 已允许两个关卡版本及 consumed_item_ids，无需改字段或工具参数。

### 冻结验收矩阵（未执行）

| ID | 最小检查与应有结果 | 关联 |
|---|---|---|
| CH01-01 | 合法首次开 R3：门开、钥匙移除、changed=true、revision+1、原 receipt 消费列表仅 emergency_key；公开 level=2.0.0/schema=1.0.0 | A02,A19,A27 |
| CH01-02 | 抽屉已开但未取钥匙首次开门 PRECONDITION_FAILED；错误配对/不可见目标拒绝；状态、消费、revision 不变 | A03,A07,A27 |
| CH01-03 | 相同 action request_id 重放和相同 committed pid 再 confirm：原 receipt/event 不变、replayed=true、当前 state；只有一条成功执行/消费事件 | A05,A21,A27,RT04 |
| CH01-04 | 新请求合法重用已开门：无钥匙也成功 changed=false，消费空数组，不增 revision；仍校验合法配对/目标可见 | A03,A07,A27 |
| CH01-05 | 开门后 R2↔R3 往返；完整 v2 手动通关，终局无钥匙，门卡保留/保险丝消费不变 | A02,A27 |
| CH01-06 | 消费后回 R2：objects 无钥匙/拾取动作；take 钥匙 ALREADY_TAKEN；抽屉观察、get_inventory、HTTP/AI 投影无再生/虚假可领取文字 | A07,A10,A11,A27,RT02 |
| CH01-07 | 同一 pid 并发 confirm 只一次 committed 消费；同版本不同有效首次请求最多一个提交，另一个 STALE_STATE；无额外消费 | A06,A21,A27,RT04 |
| CH01-08 | v2 开门前/后保存、重启恢复；后者门开且无钥匙；前者新 generation 可再次首次开门；恢复/手动变化后的旧提案拒绝、无旧版本推进 | A12,A23,A27,RT03 |
| CH01-09 | v1 快照在 v2 明确版本拒绝且当前状态不覆盖；v2 不一致钥匙/抽屉/供电状态拒绝；独立 v1 DB 回退仍保留基线钥匙 | A13,A27,A28 |
| CH01-10 | AI 先 proposal、不消费；取消不消费；confirm 真实 receipt/可见背包一致；无秘密答案/token；不宣称未执行成功 | A08,A09,A10,A11,A19,A27,RT01 |

### 有限对抗与既有回归

| 对抗 ID | CH01 后冻结范围 | 回归关联 |
|---|---|---|
| RT01 提示注入 | 问题/可见文本夹带绕过确认或输出未发现答案；白名单/可见投影不扩权；mock 脚本范围与真实语言鲁棒性分开报告 | A07,A08,A10,A17；CH01-10 |
| RT02 隐藏对象 | 未开抽屉访问钥匙/未知线索拒绝；已消费后重拾拒绝、抽屉不再生 | A07,A10,A17；CH01-06 |
| RT03 旧提案 | 手动变化/restore 后 confirm；未执行旧动作，旧 generation 明确失效 | A09,A23；CH01-08 |
| RT04 重放并发 | 同开门 pid 并发 confirm、相同 request_id 重放、新请求重用；核对 receipt/事件及无额外消费 | A05,A06,A21；CH01-03/04/07 |
| RT05 越权会话 | A token 读取/写入 B 状态、存档、提案均拒绝/null state，不改变 B | A14；确认与存档回归 |
| RT06 证据注入 | 评价器读取夹带跳过校验/不存在 Evidence ID 的材料，可信契约不被覆盖，虚假引用不能 PASS | A25；E2/E3 独立评价入口 |

回归保留 R01–R18 与 A01–A28，不以 CH01 替代既有范围。QA 持有 tests/，v1 旧结果/原始证据不改；v2 新运行以 level/源码哈希绑定。当前 test_m2 的基线钥匙保留、终局背包、快照反向版本断言需 QA 按候选版本调整或明确基线分组，不能靠删除断言制造通过。重点 Claim：首次原子消费、重放并发无二次消费、投影/恢复无再生；其余纳入已有回归。Finding 记录真实输入/版本/预期/实际/Trace/Owner，修复后独立 QA 复测；没有反例也只报告实际覆盖。

### T29 Backend 明确任务卡

前置：Main 接受此 T28 规格；仅改 Backend 所有路径 `backend/app/domain/`、`backend/app/api/`、`backend/app/storage/`、`backend/app/main.py`，不改 tests/、contracts/、archive/、旧证据或其他 Owner 文件。

1. 分离 SCHEMA_VERSION=1.0.0 / LEVEL_VERSION=2.0.0；首次成功钥匙开门同时移除物品，消费列表仅一项，message 说明真实消费；失败、已开门重用保持既有语义。
2. 用既有 r3_unlocked 表示已消费；修正钥匙可见性、已领取判断、抽屉 inspect 文字和 v2 不变量，拒绝重新生成或持钥匙且已开门快照，不增公开字段。
3. 保持原子事务、不可变收据、版本冲突、一次性提案规则；验证重放原 receipt 不重新执行、当前 state 投影正确。核对 v1 快照拒绝/v2 保存恢复/新 generation，以局部临时 DB 验证，不接触现有 DB。
4. 提供局部验证命令、真实 exit、源码哈希、结果证据、新失败与限制；交 Main 冻结候选后 STOP，不自行签 A27/T30 正式 QA。

Frontend/AI：各 Owner 核对确认前/后背包与真实消费反馈、重放原 receipt 和当前 state 的含义、上下文投影/工具结果一致；通用展示若已满足则可不改代码，但报告实际检查范围。Delivery：后续交接用独立 v1 DB 验证回退，不覆盖基线 archive。QA：Main 稳定候选 GO 后执行矩阵/RT/必要回归，保留旧失败、修复和复测证据。

T28 的 `contracts/check_contracts.py --output <new-path>` 只新增可指定报告路径，默认兼容；新报告保留 `contracts/validation.json` 历史内容。该检查仅验证公开契约结构，不能代表游戏运行、模型调用、正式 QA、课程批准或完整 Draft2020-12 实例校验。准确命令、exit 与哈希另交 Main 证据索引。

## 当前升级接口 v3.2

升级设计以 `docs/upgrade-plan.md` 为主基线；以上 v1/v2 工程卡保留历史语义。`create_app()` 默认 legacy（level2.0/schema1.0）；显式 `gameplay_version="v3.1"` 保留上一升级规则（level3.1/schema1.1）；`upgrade`/`v3.2` 选择本版（level3.2.0/schema1.2.0）。生产 module app 默认 upgrade；默认数据库分别为 game.sqlite、game-v3.1.sqlite、game-v3.2.sqlite。旧数据库不迁移、不删除。跨版本恢复拒绝 SNAPSHOT_VERSION_MISMATCH，不覆盖当前会话和原槽；同版本缺失字段、额外字段、非法生命周期或矛盾观察事实拒绝 INVALID_SNAPSHOT。恢复沿用既有原子事务和新 generation。

公开 visible_state 使用三个独立严格分支，保留旧字段/enums/additionalProperties=false。新版必有四个 device_states、observed_object_ids，以及 puzzle_states：microscope=EMPTY|SLIDE_PLACED、panel=EMPTY|STRIP_INSERTED。槽状态只表示物品安装；样本读数由发现的线索表示，终检完成沿用 progress.check_done。服务端另保存 required taken_item_ids/consumed_item_ids，不公开答案。物品 usable_targets 保持字段但为空。

手动工具仍支持原六个动作及 `interact {target_id}`，新增 `submit_login {target_id,username,password}`。登录仅 r2_monitor 的 LOGIN_LOCKED 阶段；用户名 1–64 字符 [A-Za-z0-9_-]，密码 1–16 位数字，原样精确匹配，不去空格、不接受额外参数。格式错误 BAD_ARGUMENT，错误凭据 WRONG_CODE，失败不改变状态或版本。登录 affordance 的 arguments 只有 target_id，requires_code=false；界面据 tool 展示两个输入框。每对象最多一个推进 affordance，inspect 可并列。provider tools 仍为原六个，AI 不提供 interact/submit_login。

观察后才能操作当前可见对象。普通 r1_door/r2_door 观察后 interact 拉开门闩即可跨房探索；无需电源或登录。设备仍有完整柜门、电箱、电脑、出口阶段，每阶段由明确动作推进。保险丝安装不能直接供电，电脑读取必须经过启动和登录，出口刷卡不能直接开门，纸条安装与终检通过后仍需释放门锁、推门、move EXIT。

inspect 仅登记本次可见对象的观察及当前可得谜题线索；中性外观不创建虚构 observation clue。样本读数只能在玻片已安装时取得，纸条只有 DATA_READ 后可见。AI read callback 校验知识单调、声明一致、版本增量一致、新知识属于本次调用前可见目标，禁止读取改变背包/房间/状态/设备/物品槽/进度/出口/存档/会话/版本；get_inventory 不能新增知识。猜中正确输入允许，但真实物品、电源及设备阶段前置不能绕过。

本节是接口与行为规格，不代表 QA 已执行；实际命令与结果另存各版 evidence。

## 当前升级接口 v3.3

`upgrade`/`v3.3` 选择 level3.3.0/schema1.3.0，默认 game-v3.3.sqlite。显式 v3.2、v3.1、legacy 保持原规则、独立数据库及严格投影；create_app() 的默认 legacy 不变。旧存档无自动迁移，跨版本拒绝 SNAPSHOT_VERSION_MISMATCH；已存在数据库不删除或重置。

沿用四设备链、显微镜和纸条两个物理槽，新增服务器 required circuit_rotations（九项整数0–3）。公开 minigames 必有 circuit/sequence 两个 nullable 字段。电路只在当前R2、电箱已观察且 FUSE_INSTALLED/CIRCUIT_READY/POWER_ON 暴露；顺序只在当前R3、控制台已观察、纸条已插且出口处于 FINAL_CHECK/UNLOCKED/OPEN 暴露。初始及其他房间投影为空，不把未来盘信息送到模型。AI read guard 将 minigames 视为受保护游戏字段。

线路盘3×3，module_id=c00到c22行主序，shape=I|L，rotation=0|1|2|3。零旋转I端口N/S、L端口N/E，每次顺时针90度；side=N|E|S|W。公开source/sink为module_id和side，modules含row/column/shape/rotation，status=editing|completed。rotate_circuit {target_id:r2_powerbox,module_id} 将部分旋转持久化；submit_circuit {target_id:r2_powerbox} 遍历相邻模块互惠端口，必须连接公开source到sink。无固定期望角度数组、无客户端solved字段；等效180度直线及无关模块旋转也可通过。通过才到 CIRCUIT_READY，之后普通 interact 合总闸到 POWER_ON。通过盘冻结；FUSE_INSTALLED 的普通 interact 不能旁路。保存、恢复、读状态和重启均复用原Store事务，部分旋转属于存档game_fields。

submit_sequence {target_id:r3_panel,device_ids} 要求恰四个唯一合法标识 cooling/lighting/safety/ventilation；控制台已观察并插纸，出口 FINAL_CHECK 且尚未完成。按钮公开设备名和符号，布局 cooling▲、lighting★、safety●、ventilation■，与源序不同；完整答案由R1源序、R2读取位置和R3对应规则推导。旧 r3_panel submit_code 一律无法完成新版终检。成功保存 check_done，但出口仍需释放门锁、推门和移动。未提交顺序草稿仅前端，reload/restore/房间切换时清空，不纳入存档。

三个新动作仅手动接口，不加入原六provider tools。额外字段、非法module/device、重复device、错误长度拒绝 BAD_ARGUMENT；目标不可见 NOT_VISIBLE；未观察、物理阶段未到或已冻结 PRECONDITION_FAILED；合法格式但线路未通/顺序错误 WRONG_CODE，无正确答案回显、无道具/真实进度破坏。所有修改仍受revision/generation/request_id约束。本节为行为规格；自验和独立QA事实另见v3.3证据。

## 当前完整灰盒接口 v3.4

2026-10-08 控制台显露调整：仅 v3.4 在当前 R3、控制台已观察且研究纸条已插入时公开四设备的名称与图形，不再等待出口刷卡和 FINAL_CHECK。前端可保留本地顺序草稿，但 submit_sequence 操作提示与服务端提交仍要求 FINAL_CHECK、纸条已插且终检未完成；提前提交为 PRECONDITION_FAILED，不计错误或推进状态。旧 v3.3 显露时机不改，level3.4.0/schema1.4.0、存档字段与校验不改，同版本旧存档按保存的事实重新投影，无迁移或记录重写。

`upgrade`/`v3.4` 为 level3.4.0/schema1.4.0，默认 game-v3.4.sqlite；显式 v3.3/v3.2/v3.1/legacy 保留旧玩法和独立数据库。create_app() 默认 legacy 不变；跨版本快照明确拒绝、不自动迁移。四设备链、两个安装槽、三个房间、四物品和两个小游戏全部沿用；未引入Phaser、美术、额外强制谜题。

服务器required statistics保存 started_at、finished_at（未赢为null）、current_hint_level（1/2/3）、hint_count、mistake_count。公开 statistics另含clues_found/clues_total=10及hidden_found/hidden_total=2；没有随时间自发变化的字段，同revision投影保持稳定。前端可按started_at显示当前计时；只有won的nullable settlement返回服务器固定elapsed_seconds、线索/提示/错误/隐藏计数和rating=S/A/B/C。elapsed取服务端持久起止UTC差，包含离线时间、赢后冻结，不代表真人实测游玩时间。统计随slot保存恢复；reset新起止/统计、新generation，保留旧slot，restore返回保存的同一run。恢复后的提示和错误计数也回到slot事实。

两条可选故事线索：R1柜ITEM_TAKEN后r1_photo→r1_photo_clue；R2电箱POWER_ON后r2_service_label→r2_service_clue。都是当前房间中实际暴露对象的inspect，未暴露访问NOT_VISIBLE；不增物品、设备或通关门槛。已有八线索加二故事线索，总数10，hidden总数2。

旧版AI协议和行为保留。仅3.4 AI请求接受hint_level整数1–3（省略默认1），额外字段/布尔或非法等级BAD_ARGUMENT；响应仍为原answer/clue_refs/status/proposal/usage。3.4没有进度提案、没有自动inspect，proposal固定null；HintCallbacks拒绝读工具/提案。必要已发现关系或当前暴露线路不足时begin_ai直接缓存no_suggestion，model_calls=0，不调用运行时/provider、不计提示。提示等级只在有可提示主题的reservation接受并保存，改变等级同步增加revision并以新cursor绑定轮次。

等级1给方向，等级2指向已经发现的焦点，等级3仅给部分关系。提示主题仅来自已发现record+clock/sample、plaque/clock+maintenance、symbols+indices+legend，或当前暴露editing线路的公开接口。新helper不导入任何私有答案；provider仅收到可用topic/ref IDs，不收到历史动作、玩家问题、完整私有状态或解法。真实provider只选择严格{topic,clue_refs}且匹配已知允许项，tools为空；默认mock在本地选择固定主题，真实model_calls=0，不虚构token用量。保留既有provider、请求header、凭据、固定模型和canonical budget。最高提示也不显示完整柜码、完整登录值、完整线路路径或四设备答案。

finish_ai在原receipt事务再次按当前knownrefs和接受等级重渲染，运行时自由文本无权进入提示，包括stopped文案；候选提案和未知引用拒绝。合法提示完成才hint_count+1且revision+1；failed/stale/unknown/replay不加提示。请求重放使用原receipt并返回当前投影，不能再次运行模型或统计。统计增加后先保存会话再完成AI receipt，避免拆分计数提交。

meaningful错误只包括实际手动动作的WRONG_CODE（柜/登录/线路/顺序）或手持物品对当前可见且已观察对象的错误配对。原409错误码仍返回，mistake_count与revision各+1，谜题/背包不变；schema/auth/stale/未看见/未观察/正确配对但阶段不足不计，旋转或普通观察也不计。失败同request_id重放不再计。提案precheck只读副本，从不计错误。

评级规则公开：S需发现至少9线索、提示最多1、错误最多2；否则A需至少7线索、提示最多3、错误最多5；否则B为提示最多8；其余C。时间不参与评分，等级不影响胜利。本节为行为规格，不替代实际自验、独立QA或真人反馈。

## 手动多时刻存档（v3.4增量功能）

用户授权在当前认证游戏会话中自由保存多个时刻并选择恢复。游戏level3.4/schema1.4、快照版本、原单槽save/restore、各旧版入口/数据库隔离、谜题和AI行为均保持原语义。没有云账户、导出、自动保存、删除或重命名功能。启动只CREATE TABLE IF NOT EXISTS添加save_slots及其session索引，不迁移、覆盖或删除原saves数据。前端保持当前session capability绑定。

新增三路由，均要求原X-Session-Token：GET /api/sessions/{id}/saves→200 data{slots,visible_state}；POST同/saves→201，body原request_id/revision/generation加可选name（字符串最多40字符；省略、空或仅空白由服务器自动命名）；POST /saves/{save_id}/restore→200，body原VersionRequest。两个修改响应都为data{request_id,replayed,slot,visible_state,message}，create_save_request契约用两个严格对象分支表达可选name。命名按普通文本展示，不接受额外字段或非字符串。

slot公开元数据严格包含save_id、name、saved_at、schema_version、level_version、source_revision、source_generation、room_id、status、clues_found、kind。新archive的房间、playing/won和已发现线索数均来自该保存时刻的真实状态，不公开快照、物品私有记录或秘密答案。archive按created_at DESC,rowid DESC稳定排序，同一时间戳也新记录在前。旧单槽若存在则最后追加save_id=legacy/name=旧版单槽存档/kind=legacy，room/status/clues_found为null，因为只读取原公开summary、不解析或重写原私有snapshot用于列表。

每次创建独立save_id，append-only；同一名字、状态、revision或时间仍可另存新记录，只有原request_id的完全相同重放返回原ID，不能生成重复存档。新save不改变状态revision/generation、不触及原单槽和visible_state.save。reset新游戏但保留所有历史archive及旧单槽，重新打开同一会话后仍可列表和选择。

选读archive及legacy均复用原validate_snapshot的完整版本、归属、校验和、时间、字段及规则不变量验证；成功才原子替换游戏状态，以当前revision+1及新generation恢复，保存时刻的设备、背包、旋转、统计和run起止事实同步恢复，失效旧AI轮次/提案。原存档记录不变。未知或其他会话的save_id一律SAVE_NOT_FOUND404，不泄露归属；token越权FORBIDDEN_SESSION403。损坏INVALID_SNAPSHOT409，跨版本SNAPSHOT_VERSION_MISMATCH409，失败不覆盖当前状态或存档。

新archive路由在认证及参数验证后，先检查共享action_receipts的完成请求：完全相同请求重放原不可变event/slot结果并提供当前visible_state，replayed=true；即选读已经换generation，也不会再次恢复或回滚后来的动作。请求ID替换operation/save_id/name等内容REQUEST_ID_CONFLICT409。没有完成receipt的新请求仍必须匹配当前generation/revision，否则STALE_GENERATION/STALE_STATE409。旧execute的generation优先策略不改。本节是规格，实际自验和独立QA结果存于evidence/integration/multiple-saves/。
