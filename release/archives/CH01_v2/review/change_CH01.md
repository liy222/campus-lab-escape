# CH01 Main engineering change registration

Approved by Main under the human project development request. Teacher approval and human signoff remain null. The following acceptance card is copied from the stable T28 Spec; implementation and QA are separate future evidence.

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
