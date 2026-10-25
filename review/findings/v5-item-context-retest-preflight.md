# 单 G3 叙述复测提案：独立 AI QA 离线预检

日期：2026-10-24。结论：**当前单次提案的有限离线预检通过，尚无新付费授权，不可据此执行。** 实际执行者为独立 AI QA 智能体；没有真人或教师参与此语义复核、试玩、签字或接受。

## 精确绑定与拟议范围

新 runner `evidence/upgrade/v5.0/blueprint-item-context/real-samples/run.py` SHA256：`eed8325b4cff57668eb36ec5d3584b1ef270080b59f69755a946f7190d2b38cf`。它从原已封存 `31d72c5c...` 执行器派生，原件不改、不重跑。

Main 仅实际执行一次纯 `--prepare`，exit 0；QA 没有重复 prepare。实际预览绑定当前 410 来源、候选原字节和新 runner，共 412 来源，bundle 为 `6232d032655ecf5a894dd60e82cb782fd175ebe71c1d01194a2941ff9b14672d`，与当前文件全部匹配。

唯一拟议样本为 G3：三房 / hard / mapping_v1 / 内部受控 seed 1，与原实际 G3 完全相同的主题。最多 1 次、每项及总额均不超过 0.20 元，自动重试 0，伙伴 / evaluator 0。完整实际请求 10804 UTF-8 字节，保守输入上界 51408、输出上界 6000 tokens，预占上界 **0.150816 元**。这是离线发送前上界，不是已发生费用或账单。

实际预览包含本次 item-use 关系：item 装置指向同一 manifest 内 kind=item 的 `obj_key` 槽位，`tool=use_item`、`consumed=false`，非 item 无该字段。system prompt 与当前冻结源码相同，output Schema 不变；模型未来是否正确引用生成名称、避免虚构物品和归还 / 消耗叙述，仍未观察。

## 最小预审与继承证据

- 只读 diff 记录 `edcf7c`，exit 0：范围收窄为 G3 / 1 次 / 200000000 units，新 run ID、候选与 OUT；原 G3 case 值相同。
- 最小 scope / 路径预审 `5a68fa`，exit 0：新合法授权形状仅为 G3 / 1 / 0.20；5 个旧 scope / 放宽 cap / 旧 run ID 变体拒绝。没有创建实际批准文件。
- `Controller` AST 仅接受集合收窄；authorization AST 仅 scope 列表收窄。授权先于 marker / 配置 / Key / ledger 的 execute 前缀原样继承。finally 除结果 kind / scope / 上限摘要外与原已审代码相同，最终 source 与 safe-ledger 停止门未变。
- 复用旧 AST 与已封存局部探针，不重复原 26 项授权、5 个 finally 分支或产品测试。没有导入 runner 或执行真实 execute。
- 最终实际预览只读核对 `c7b442`，exit 0：412 来源、body hash、完整费用、同主题、当前 item_use / prompt、单次限额均一致。

新的私有定义 / witness / replay 将只在未来获准执行的 ready 分支创建于新 `OUT/raw-sensitive/`。三个精确未来路径已由现有通用忽略规则匹配，无 `.gitignore` 改动；预检时私有目录不存在。私有内容仅本地复核，不得发布或发送模型。

固定历史三条 unknown 身份 `b7490c5f157e75f973533e518a1e245c1ea0a3818318065c9c7ddf5e5b59085e`、原 10 元 cap、pending / frozen / 新 unknown / 外部 call 停止门继续继承。QA 未读取当前 canonical ledger；未来须在新的实际授权后由执行入口核对。

## 授权状态、限制与 STOP

最终检查时，新 OUT 下 `user-authorization.json`、`execute-started.json`、`dispatch-journal.jsonl` 和 `raw-sensitive/` 均不存在。预检文件不等于实际人类批准；Main 须按计划先完成正常同步，再取得新的最多 1 次 / 0.20 元明确授权并绑定精确预览 / 来源，才能进入真实执行。

旧产品 410 来源、QA 16 / 63、预检 12、实际公开 17 / 本地私有 6 哈希及旧登记 53 均保持。原 G3 finding 仍 OPEN，旧实际成功准入 / 回放与坏文本不改写；新 prepare 不证明质量修复。未来一份样本也只能支持有限观察，不能证明任意主题质量或真人体验。

本轮没有真实 Key / 配置 / ledger / DB / network / provider 访问，付费 0；不重复产品、HTTP、编译、规划、witness、构建、UI 或 evaluator。仅新增本报告与 `preflight-review*.json`。新预检结果与 seal **SOURCE STOP**，不提交、不推送、不执行收费脚本。
