# v5 道具请求上下文：独立窄 QA

日期：2026-10-24。结论：**有限纯请求合同范围联合通过；未验证真实叙述质量。** 原 G3“资料袋 / 钥匙”实际 finding 仍 OPEN，原真实输出、成功准入和回放均保留其历史 epoch。

## 实际范围与执行

新测试仅为 `tests/v5/test_blueprint_item_context.py`。正式运行前 Owner / Main 停源，Main 冻结 410 来源。没有重复编译、规划、witness、HTTP、旧套件、构建、UI、evaluation、prepare 或真实模型调用；provider、配置、账本、SQLite 和 HTTP 客户端构造边界由纯测试装置禁止。

| 实际命令 | 结果 | 证据目录 |
| --- | --- | --- |
| `python -B -X utf8 tests/v5/test_blueprint_item_context.py --candidate .../blueprint-item-context/candidate.json --output .../qa/run1` | exit 1；8 passed / 1 failed，0.41 秒；410 来源前后不变。 | `blueprint-item-context/qa/run1/` |
| 同一 runner，候选 `candidate-qa-fixed.json`，输出 `qa/narrow-run1`，仅 `--scope test_only_request_manifest_and_generation_prompt_ast_changed` | exit 0；精确 1 item；410 来源前后不变。 | `blueprint-item-context/qa/narrow-run1/` |

解释器为 `C:\Users\liyh\.conda\envs\1\python.exe`。首轮失败是 QA 使用 Git blob 原字节比较 Windows 已封存 raw，换行不同而误报 `generated.py`。产品没有变化，也没有规范化旧源码。QA 仅改用计划指定的旧实际候选 `source_sha256` 作 raw 权威，Git 仅保留 AST 对照，并为执行器增加必要的 `--scope` 适配。Main 重新冻结仅此 QA 文件后补验；其余 8 项、预算范围均未重跑。

最终候选为 `v5.0-item-context-qa-fixed-20b0be4421735bee`，文件 `evidence/upgrade/v5.0/blueprint-item-context/candidate-qa-fixed.json`，raw SHA256 `918f155521767e31dabdc9b9f8eb1a6ad0c834a82532662ee1646f713ee5aa49`。这是首轮 8 项与窄验 1 项的联合结果，不是单次完整全绿；原失败及所有原日志不改写。

## 已覆盖与人工读审

- 两族各取 3 / hard 代表，覆盖四种机制：仅 item 行带 `item_use`；槽位实际从 puzzle 的 `required_item_id` 对应到 kind=item 的 `ObjectSlot`，`tool=use_item`、`consumed=false`。其他机制不新增该字段。
- 对实际道具 ID / object slot 重命名，并放入旧 `obj_key` / `shared_key` 诱饵，输出仍跟随实际引用；返回 manifest 可独立修改，源 Blueprint 和 Schema 不变。
- 检查实际序列化消息中的关系仍指到同一 payload 内的 item 槽位；调用者 Schema、输出字段及输出 Schema 不变。自动测试不逐字断言中文提示。
- Git AST 对照证明 Backend 仅改 `request_manifest`，AI 仅改 `GENERATION_PROMPT`；内容 Schema / builder、原 compiler、provider、budget、API 和 Store 的既定冻结 raw 均不变。
- QA 人工读审新增提示：要求引用同一生成内容的物件名称，使用后保留，不另造必需物品，不追加归还、消耗或清单操作。它表达了本次输入修正意图；**提示意图不能证明模型未来遵守，也不能把旧坏文本改判为已修复。**

## 完整请求费用测量

仅用纯消息、原完整 wire JSON 与 `cost_units` 计算；没有构造 provider、读取 Key / 配置或打开账本，不把下表称为实际发送 / 拒绝测试。原生成 cap 仍为 0.20 元、6000 tokens / 60 秒。

| 请求主题 | position_v1 | mapping_v1 |
| --- | ---: | ---: |
| 6 字短主题 | 0.126072 元，cap 内 | 0.149808 元，cap 内 |
| 2000 个四字节字符 | 0.189928 元，cap 内 | 0.213664 元，超过 cap |

计算包含所有新增上下文及 Schema 字节；未提高 cap。mapping 最大主题的超限分类是纯计量结论，未重复调用原 provider 验拒。

## 证据与限制

本 epoch `qa/result.json` 和 `qa/artifact-seal.json` 绑定两个实际 run、观测、候选及本报告。只读核对旧 QA 63、预检 12、实际公开 17 / 本地私有 6 的原哈希和旧登记 53 来源；这些旧结果不被重写或重新解释。六份实际私有材料仅核对 hash，不复制内容、不发布或发送模型。

没有新产品 finding。首轮只是 QA raw 基线来源错误；当前输入缺口离线修正可接受，但真实叙述 finding、设备措辞歧义、非消耗用语限制和真人体验缺口仍在旧实际报告中。没有剩余付费授权，也没有新付费调用。既有 Starlette 弃用警告保留。

QA 新测试、结果、报告与 seal **SOURCE STOP**。后续文档、接受与 Git 由 Main / Delivery 处理；本报告不提交、不推送或宣称整体发布完成。
