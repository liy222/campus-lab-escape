# E1 实验复核 — T23 已执行，T24 超时停止，T25 待独立复核

此文件由 Main 明确 handoff 给 Experiments，仅为 T25 复核框架。T22 正在完成本地候选；T23/T24 真实模型实验尚未执行，以下不是结果、通过声明或预算批准。

待独立 QA 核对公开输入与离线资料隔离、12点来源与版本、可逆历史事实相等、六工具 schema、72行完整性、配对顺序及6行独立pilot、错误/未知/未调用保留、分母、共享原账本、有限GO、崩溃对账无重打。Owner check 与注入 mock 不能替代独立 QA 或模型观察。

T25真实结果到达后，逐条引用不可覆盖的 plan/run/input/raw/journal/summary 指纹；报告每方案 planned、付费尝试确证下界/未知、收到响应、completed、legal、correct、有效引用与用量覆盖，列举所有失败和 budget-stop。动作正确性与自由文本幻觉范围、费用上界与实际账单明确区分。不得预先填写摘要优势。

基线源码绑定依据 Main 的 `evidence/integration/baseline_v1-manifest.json`，raw SHA256 `9c36943cbb6e4fe08b6e176445ba91835fafa79a2077c2155bbf8d613f8b07c1`。其中6条旧 QA 源码记录未绑定原样保留，3个构建输出仅 runtime binding；本草案不消除这些局限。Main 最近修正的 metadata facts 不改变 baseline product，不把旧 paid scope 当实验事实。

决定留空，待 T24、QA 只读复核和 Main 确认。不证明统计普遍性、总体智能、自主通关、真人签署或课程批准。

2026-10-02独立Finding T22-EXP-001真实复现HTTP响应记录缺陷：Owner已按授权修复实验层，增加安全transport receipt观察和响应/投递三态汇总。本条不是独立复测通过声明；旧149项Owner证据及QA首轮12失败证据保留。新增Owner注入HTTP错误、坏JSON、连接错误/超时/未调用的检查仍是本地模拟，付费调用0。等待QA独立稳定复测。

## 2026-10-05 恢复及真实预试追加事实

以上条目保留为历史状态。独立 T22 恢复验收见 `review/findings/T22-acceptance-20261003.md`：764项、0失败、83条源记录前后一致，实际重跑 exit0；此验收仅是合成工程验证。旧20261002预试门已过期，旧control目录只有before快照；本次先只读原账本和27个运行记录，真实run=0，无孤立journal，无需reconcile。journal中mode=real的历史记录仅属于synthetic fixture，不冒称真实调用。恢复证据为 `experiments/runs/20261005T052614Z-readonly-recovery/recovery-audit.json`，实际命令及 exit0 见同目录 `process-result.json`。

Main 刷新公开价格证据并明确给出新有限 GO 后，本 Owner 用指定 Python 从项目根执行一次 T23 pilot，真实进程 exit0，未重试、未增加probe。命令完整记录在 `experiments/runs/20261005T052822923700Z-pilot-real-0378672e/process-result.json`。新授权为 `experiments/authorizations/E1-pilot-20261005T052732168900Z.json`，raw SHA256 `63de7ffb42753fda20fb1a201c888ca61b0cf4570c873def9c3cbaa58e85ae10`，上限6次和额外0.70元；刷新价格证据 raw SHA256 `c9cc7f4382a0e2eb9583b1120edb12238e7bb7038720a57cd6d3500d0c9eeb54`。Provider只在门检查通过后通过既有allowlist读取本地凭据；凭据未输出。

真实预试目录 `experiments/runs/20261005T052822923700Z-pilot-real-0378672e/` 保留 run/plan/6个inputs/raw/journal/completion/summary，`owner-pilot-report.json` 保存原始文件指纹与账本前后安全字段。raw SHA256 `006370fff6d61e1c3115def98cd8b5ca2de5c5d4aab71e1dce0ae432febf4643`；summary raw SHA256 `a6ee9d903668c0285d30619c0b43d93f2ca7e231560118664ebfb2e0a38fa79a`。

| 预试方案 | planned | 付费尝试确证 | 响应确证 | completed | legal | correct | 引用有效 | 引用充分 | usage覆盖 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A完整历史 | 3 | 3 | 3 | 3 | 3 | 2 | 3 | 3 | 3/3 |
| B结构摘要 | 3 | 3 | 3 | 3 | 3 | 2 | 3 | 3 | 3/3 |

六行均HTTP200，reported_model=`deepseek-flash`，无未知费用/响应、无timeout、无not_called。两方案C06均建议inspect未通电屏幕，该动作合法且引用存在，但不在冻结可接受下一步集合内，记为 `LEGAL_BUT_NOT_USEFUL_NEXT_ACTION`，未替换这两次结果。本文不把completed等同correct，也不把引用有效等同自由文本无幻觉。

原共享账本总额仍10元：调用前6条settled、charged10354480 units、experiments0；调用后12条settled、charged40106000 units、experiments6、剩余9959894000 units；pending/unknown=0且frozen=false。预试结算费用A=0.01486592元、B=0.01488560元、合计0.02975152元，区别于0.70元授权上限和0.659256元预留总界。按六行实测均值估计72次为0.35701824元；将已测输入全部按未命中缓存价格重新计费、保持相同token分布估计为0.42024元。三检查点预试不能保证正式其余检查点的用量，完整推导及7.757232元正式预留总界见该run的 `cost-estimate.md`。

实验源码及README未改，冻结仍 `f4436d0b4d9009788993092246b278e44c03021558bddb8b87337372b3eb1066`，pilot plan仍 `476f4615855eac7d6a24322358e1a17635ffffe45b3f06ee4dc5c1d1ed24558b`；游戏v1 manifest绑定和既有6条旧QA未绑定/3个runtime-only局限保持原样。预试只表明真实入口和计费字段可取得，不能支持摘要优势或正式结论。T24尚未执行，须独立只读复核和Main单独有限GO；T25及实验决定须在T24和独立复核后形成。没有人类签署或课程批准。

## 2026-10-05 T24 正式执行与保留停止结果

Main只读复核预试计划、6行known usage/HTTP200、输入与summary，并接受C06真实偏差作为实验结果保留后，另发正式有限GO。授权 `experiments/authorizations/E1-formal-20261005T053235072095Z.json` raw SHA256 `c326387edf396cf4d5adefc4109a46b2df5f7acf3e924eac3e12ef518a937660`，max_calls72/额外8.00元，仍共享原10元账本。实际只执行一次指定runner，session82634，完成chunk8b04ad，exit0；完整命令见正式run的 `process-result.json`。exit0表示已按执行门保存终态，不表示72次响应全部完成。

正式目录为 `experiments/runs/20261005T053334004502Z-formal-real-48d972eb/`。72行原顺序终态完整：22 completed、1 timeout、49 not_called。第23行 `formal-C12-full_history-1` 发生MODEL_TIMEOUT，HTTP响应、上游投递、reported_model和usage均null；原共享ledger call `520a5c50b9204960a3f9915952ed9b97` 保留unknown最大预留0.16292元。停止原因 `STOP_AFTER_UNKNOWN_TIMEOUT_OR_PROVIDER_ABNORMALITY`，未重打、补打或替换任何失败。原始completion已存在，不是崩溃丢行，也无需reconcile；只读reconcile不能证明超时上游用量或授权重发。

| 正式方案 | planned | 付费确证 | 响应确证/未知 | completed | timeout | not_called | legal/completed | correct/completed | correct/planned | 引用有效/completed | usage覆盖/planned |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A完整历史 | 36 | 12 | 11/1 | 11 | 1 | 24 | 11/11 | 8/11 | 8/36 | 11/11 | 11/36 |
| B结构摘要 | 36 | 11 | 11/0 | 11 | 0 | 25 | 11/11 | 9/11 | 9/36 | 11/11 | 11/36 |

只取得第一重复C01–C11的11个完整配对，不能按完整12点×3重复报告。五条已完成但不正确建议均为合法且不推进的inspect：C05 A/B查看r1_door、C06 A/B查看未通电r2_monitor、C08 A查看r2_door；原raw完整保留。有效引用与正确动作判定不能证明自由文本全部事实准确，不能把8/11对9/11当成B优势结论。

正式账本费用上界0.23749696元，其中22次已知结算0.07457696元、1次超时未知最大预留0.16292元。A上界0.18954440元包含超时预留，B=0.04795256元，不能直接据此比较成本。已知usage合计prompt46668/output3394/cache_hit23424/total50062。原共享ledger调用前12settled、charge40106000 units；调用后35条（34settled+1unknown）、charge277602960 units、remaining9722397040 units、frozen=false。尽管数值额度尚有剩余，unknown1阻断后续任何真实付费phase；未结清未知账本、不新建allowance。

raw SHA256 `74c20c72ac39e236bd3e5c48062f71e2c98a92b9368269c3e67a95c841db2e28`；summary raw SHA256 `83870be5f56b8f53a4c5be6a42fe049aee78c8159dac872f20ef04c74a4ecb11`；`owner-formal-report.json` raw SHA256 `031d6056afa4eafe6607e0f90ac5c30bbbf5284e876144091ff5bab17736c10d` 包含72行安全状态/usage/cost、全部原输入产物hash及原账本前后字段。`owner-interpretation.md` 为本Owner解释草案。Owner只读会计命令exit0；一次只读辅助统计先因str/Path类型错误exit1，纠正调用后exit0，详见process-result；没有改稳定源码或增加模型请求。

T24真实尝试及止损行为已有证据，但完整72条响应目标未达成；T25只读QA复核与Main决定仍待完成。参数/源码未因偏差或timeout修改，旧baseline6条未绑定/3个runtime-only局限保留。价格、输出长度和缓存效果只适用于这次运行；无需填入摘要获胜、真人签署或课程批准结论。

现场还原补录：超时第23行start=`2026-10-05T05:34:18.979494+00:00`，账本created=`2026-10-05T05:34:18.992257+00:00`，row end=`2026-10-05T05:34:39.008228+00:00`，测得latency20.0267483秒。请求UTF8 bytes17317、input token bound77460、max output1000，reservation/charged均162920000 units；未知prompt/completion/cache仍null、reason=MODEL_TIMEOUT、state=unknown。未知范围包括供应商是否收到/完成请求、真实HTTP状态、真实reported model及token用量；不得将最大预留等同真实账单，也不推定请求未到达。新增 `source-timeout-accounting.json` raw SHA256 `4ce3bc338f19ede3307525b7a544b8dde105800a7d32ca65d69c5522bbadeb4a`，记录41条before/after源图，明确before来自原formal plan.freeze.source_hashes（runner生成时记录，非补造Owner前快照），after为当前实际raw bytes哈希，全部相等；同时含timeout原row和原账本安全字段及原产物指纹。原raw/plan/summary/journal未改。后续真实calls保持hold；是否解除须Main专门预算复核，Owner未修改门或账本。
