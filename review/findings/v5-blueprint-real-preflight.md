# v5 蓝图生成 R4：独立离线预检

日期：2026-10-24。结论：**当前精确执行器与实际离线预览的有限预检通过；尚无付费授权，不可据此执行。** 没有实际生成、模型质量、准入成功或 HTTP witness 成功结论。

## 绑定对象

- 当前 runner：`evidence/upgrade/v5.0/blueprint-generation/real-samples/run.py`，SHA256 `31d72c5cf6e84cde83d371a3849a4793896758e4d87c0d7b2148fe1fcb1781f0`。
- Main 实际 `--prepare` exit 0，QA 没有重复 prepare。预览 `offline-preview-v1.json` SHA256 `fec5789db9d55f76928ba68902d85655cfb6cca1ed5537315ed9d4fb51151d95`。
- 预览绑定 409 个已接受候选来源、该候选文件原字节及 runner，共 411 来源；独立当前哈希全部匹配。来源 bundle 为 `207b07f44f5070ae499f892c4ff2ca49c9cc89f8de3604571d0cc35bbad415b3`。
- 原 R0–R3 的 63 份封存证据、旧评价登记 53 个来源均仍匹配，未修改、重跑或重新登记。

## 实际请求检查

QA 独立重算完整实际 JSON 字节、4 倍字节加 8192 的输入上界、6000 输出上界及原费用单位，并核对实际 system prompt、主题、requirements、已选骨架、exact schema 和 Host seed。

| 样本 | 规模 / Host 选择 | 请求字节 | 保守上界 |
| --- | --- | ---: | ---: |
| G2 | 2 / normal；seed 0；position_v1 | 5823 | 0.110968 元 |
| G3 | 3 / hard；seed 1；mapping_v1 | 10509 | 0.148456 元 |

两项合计预占上界 0.259424 元，低于拟议总上限 0.40 元；各项仍受 0.20 元、6000 tokens / 60 秒限制。拟议名额严格为 G2、G3 各一次，最多 2 次，无重试、伙伴或 evaluator 调用。以上费用是发送前保守上界，既不是账单，也不是新增授权。

## 初始发现与修正

最初作者报告对应旧 runner `72f8e485...`，该报告和首次预审 `preflight-review-draft-v1.json` 保留。Main 接受以下窄修后，Owner 停源为当前 `31d72c5c...`；QA 仅复核，不改 runner。

1. 初始账本门槛只有 unknown 数量 3，不能证明仍是历史三条。当前固定并检查封存身份哈希 `b7490c5f157e75f973533e518a1e245c1ea0a3818318065c9c7ddf5e5b59085e`，与历史 round3 的封存摘要独立匹配。QA 未打开当前 canonical ledger。
2. 末次发送之后，旧代码仅记录 `source_after` 而不等于预览来源。当前 finally 明确比较，变化或不可读均降为 exit 1，保留准确停止原因与 finalization failures。
3. 旧代码最终直接读取 ledger 快照且不将异常降为失败。当前最后快照走 `safe_ledger`；新 unknown、外部 call 或不可读均降为 exit 1。
4. 旧代码在 TEMP DB 删除后只留 witness hash / count / settlement。当前仅在 ready 后持久化本地脱敏完整定义、完整 witness、逐动作 HTTP 状态与 API / state hash、最终状态。Main 明确本轮只验证真实生成准入与 HTTP witness，字段 `real_api_save_restore_tested=False`；**不声称本轮重复验证了 save / restore**。

未来 `G2/G3-private-definition-local.json`、`-witness-local.json`、`-api-replay-local.json` 六个精确路径经 `git check-ignore --no-index` 确认被忽略。它们含测试答案材料，仅本地复核，不发送模型或发布；此时文件尚不存在。

## 最小必要隔离探针

未导入 runner，未运行真实 `--execute`。QA 仅编译抽取的授权函数、缺授权前置分支及 finally AST；使用隔离 OUT、合成数据和 stub 来源 / 账本 / 输出，运行时 import 与 marker / journal 写入均拦截。

| 实际命令 | 结果 |
| --- | --- |
| `python -X utf8 -`，隔离 guard / finally AST 探针，记录 `0aa42c` | exit 1：QA wrapper 未传 `exit_code` 参数；不是 runner 缺陷。 |
| 同范围 wrapper 窄修，记录 `244e51` | exit 1：QA wrapper 缺少 `re` 依赖；不是 runner 缺陷。 |
| 同范围 wrapper 补齐，记录 `76500e` | exit 0：26 个非法授权变体拒绝；缺 fresh auth 在 marker / import / 配置之前拒绝；5 个 finally stub 分支符合预期。 |
| `python -X utf8 -`，只读预览 / 来源 / 费用 / 忽略规则核对，记录 `e38f8b` | exit 0：411 来源、两个实际 payload 与费用、6 个忽略路径、旧 63 / 53 来源全部匹配。 |

两次探针 wrapper 失败保存在 `preflight-review-probes-first-failures.json`，最终探针记录为 `preflight-review-probes-v1.json`。没有为报告重复执行，没有扩展产品测试矩阵。探针全部实际 runtime imports 0、marker / journal 写入 0，隔离 OUT 无文件；没有读取真实 Key、配置、账本、数据库或调用网络。

## 授权与停止边界

静态核对：实际生产 `GenerationService` 保持原样注入，仅在隔离进程控制 Host 的一次骨架选择；模型内容仍须原样通过原准入，不修复、不替代、不调用 fixture。授权文件绑定预览原字节哈希、411 来源 bundle、准确 G2/G3 scope、精确整数 2 次 / 400000000 units，以及实际人类批准引用；检查位于一次性 marker、配置、Key 和账本访问之前。marker 独占创建，before-dispatch journal 先落盘；失败也消费名额，不自动恢复、补发或重试。

最终只读检查时，`user-authorization.json`、`execute-started.json`、`dispatch-journal.jsonl` 均不存在。该事实与本预检不能替代真实用户批准。未来 Main 必须先取得并记录新的有限授权，再在真实执行入口核对当前 canonical ledger、固定历史 unknown 身份、pending / frozen 和 exact source / payload；任何条件失配即停止。

## 限制与 STOP

本轮 QA 实际 paid / provider network / config / Key / canonical ledger / DB 访问均为 0；没有重复产品测试、构建、浏览器或评价。历史 unknown、真实失败和旧评价缺证结论保持原状。guard 探针是合成局部检查，不能证明真实供应商、全运行时路径或任意主题可靠。

本预检只允许交付“待新授权的精确执行提案”，不证明真实模型输出、叙事质量、可玩性或发布接受。实际执行后仍需逐项只读独立结果复核。QA 新预检文档 / 证据 **SOURCE STOP**；不提交、不推送、不执行付费脚本。
