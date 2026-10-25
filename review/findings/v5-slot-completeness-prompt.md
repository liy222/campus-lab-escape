# 额外资料物件槽位提示澄清：独立 AI QA

日期：2026-10-25。结论：**现有五项纯检查一次通过；仅接受有限离线提示 / 合同检查，不证明真实生成或叙述质量改善。** 执行者为独立 AI QA 智能体，不是真人或教师审查、试玩、签字或接受。

## 来源与实际运行

冻结候选 `v5.0-slot-completeness-71155c8b17d70383`，文件 `evidence/upgrade/v5.0/blueprint-slot-completeness/candidate.json`，410 来源。相对前一接受的 410 路径，仅 `backend/app/ai/v5.py` 的 prompt 原字节变化；其余 409 路径 raw 相同。AI 非 prompt AST、GenerationService、Schema、组装器、规则、provider、budget、API 和 Store 保持原有实现。

实际命令为指定解释器下的原测试：

`python -B -X utf8 -m pytest tests/v5/test_blueprint_item_context.py -k "only_request_manifest_and_generation_prompt_ast_changed or messages_serialize_item_interaction_contract_without_output_schema_change or whole_request_short_and_four_byte_theme_budget_measurements" -q -p no:cacheprovider --junitxml=<新 qa/run1/junit.xml>`

工具记录 `0ea555`：exit 0，**5 passed / 4 deselected，0.24 秒**；410 来源 before / after 完全一致。范围恰为既有 AST 1 项、序列化消息 2 项、完整请求预算 2 项，没有写新镜像测试，也没有重跑另四项道具派生检查。完整实际命令、候选原字节哈希和来源见新 `qa/run1/run.json`；`57f8d3` 只读结果 exit 0。

## 新观测路径的归属

准备检查 `8f8d36` 发现旧 `observe` 有固定目录 guard，故正式运行前 Main 明确授权唯一新路径：

`evidence/upgrade/v5.0/blueprint-item-context/qa/slot-completeness-20261025-run1/observations/`

这三份观测属于**本次新候选**，不是历史 item-context QA 的补全。wrapper 在 pytest 启动前实际确认整个新观测父目录不存在，并记录此事实；新 `slot-completeness/qa/run1` 用 `exist_ok=False` 创建。观测仍由原 `observe` 原样写入，其 `mkdir(..., exist_ok=True)` 不是 OS 级原子独占，本报告不作该声称。

原测试、observe、driver、fixture 和断言均未修改或替换；新 output / JUnit / run / result / seal 均在新 slot-completeness namespace。旧 16 份封存路径原字节不变，没有因计划路径元数据或并发检查而重跑测试。

## AI 语义复核与合同范围

独立 AI QA 读取新 prompt，确认其明确区分 `extra_digits` / `extra_devices` 参数数组与 objects 资料物件；仅当 Schema 要求四个命名额外槽位时，要求各自填写 name / description，并要求 room / object 键集合等于对应 required 集合、不增加未要求槽位。文字表达的是按 Schema 条件处理的意图，不是无条件让 easy 请求插入额外物件。

完整物件同名引用及 `consumed=false` 使用后保留的原约束仍在。程序不补缺项、不改 Schema、不放宽拒绝、6000 token / 60 秒 / 0.20 元 cap，也不增加重试或回退。五项检查覆盖现有代表请求的序列化关系、Schema / caller 不变以及冻结实现边界；没有新增 easy 生成、编译或模型服从验证。

这些是输入意图和接口检查，不能保证实际模型填齐槽位，不能据此声称叙事自然、可靠或旧 finding 已关闭。

## 四个完整请求预算观测

主题分别为 6 字短主题和 2000 个四字节 Unicode 字符；使用三房 hard 的两族请求。计算包含整个 wire JSON、完整 Schema 与新增文字，只有纯计量，**没有真实发送或 provider 拒绝测试**。

| 请求 | position_v1 | mapping_v1 |
| --- | ---: | ---: |
| 短主题 | 8055 字节；0.128824 元，cap 内 | 11022 字节；0.152560 元，cap 内 |
| 2000 四字节字符 | 16037 字节；0.192680 元，cap 内 | 19004 字节；0.216416 元，超过 cap |

原 cap 仍为 0.20 元。以上是保守请求上界，不是账单、实际消耗或新收费提案。未重复 prepare，也未追加同主题纯测量。

## 历史结果与限制

旧真实单 G3 运行仍为 **exit 1 / rejected / MODEL_INVALID_OUTPUT**：遗漏四个必需物件槽位，未准入、无定义或 witness。该真实原稿、原诊断、14 份实际封存证据及所有旧 QA / 预检 / 私有哈希与旧登记 53 均保持。旧实际 412 来源图是历史快照，**不声称它仍与当前 prompt 相同**；仅新 410 候选与本次实际运行匹配。

只读完整性核对 `55261b` exit 0，确认唯一 prompt 文件 delta、旧 63 / 16、预检 12 / 8、旧实际公开 17 / 私有 6 / 最新实际 14 的固定路径哈希和旧登记 53 原字节均保持。没有重新诊断旧 raw、编辑失败状态或混入新源码解释。原真实叙述 finding 仍 OPEN，尚无新真实复测。

本轮 provider / config / Key / current ledger / DB / HTTP / 编译 / solver / witness / build / UI / evaluator / model / paid 调用为 0。既有 Starlette 弃用警告保留。没有真人质量评估、总体成功率、发布接受或模型遵守保证。

新结果、报告及 seal **SOURCE STOP**。本 QA 不修产品、不提交、不推送，不提出或执行新收费请求。
