# T26-EVAL-001：共享账本未知调用未阻止评价请求

状态：独立最小反例已复现，等待 Main 处理及 Owner 修复稳定；尚未复测通过。

`evaluation/provider.py` 的 `ExistingLedger.reserve` 只检查当前 approval ID 前缀下的未结算行。其他 game、experiments 或另一 approval 的 evaluation 未知行不会阻止新的评价请求。正式 QA 任务要求共享生产账本存在 unknown/pending 时在网络前拒绝。

三个隔离假账本分别放入上述 scope 的 unknown 行；`FakePaidProvider` + `httpx.MockTransport` 都执行一次传输，追加新 settled evaluation 行。共享总额仍计入未知预留，本例没有证明超过 CNY10；证明的是不确定调用停止门被跨 scope / approval 绕过。

实际命令 `C:\Users\liyh\.conda\envs\1\python.exe -B -X utf8 -m tests.review_evaluation --unknown-only`，exit1，5 断言中 3 失败。fresh process 的 `backend_modules=[]`，Evaluator 源 before=after。证据 `evidence/qa/T26-evaluation-20261002T125742148749Z/result.json` 和 `unknown/*-result.json`，原记录保持。

实际付费请求 0，实际网络 0；仅 QA owned 假账本，不打开原共享账本、不读取 `.env` 或任何凭据、不导入 backend。修复应在 ExistingLedger 事务预留中检查全部 scope 的 reserved/unknown，并保留原 cap、金额和行。需要独立复测，不更改冻结游戏 Provider。

## 2026-10-03 稳定预算修复独立复测

本 Finding 的预算停止门范围已通过独立复测，**关闭 T26-EVAL-001**；T26 整体验收仍待新增 [T26-EVAL-002](T26-EVAL-002-unvalidated-audit-suggestion.md) 修复后通过。

真实命令 `C:\Users\liyh\.conda\envs\1\python.exe -B -X utf8 -m tests.review_evaluation`，完整进程 exit1（179 项仅 EVAL-002 的非法审计字段断言失败）。独立矩阵覆盖 game/experiments/probe/同 approval 与另一 approval 的 evaluation，各放一条 unknown 或 reserved，共10种场景：全部 `PRIOR_CALL_UNKNOWN_STOP`、传输 dispatch 0、provider calls 0、旧行完全保持、新行 0；全部 scope settled 对照允许1次合成传输及1新 settled 行。矩阵21项断言全部通过，不以 overall exit1 隐藏该失败，也不把本窄范围通过作为全部 T26 通过。

稳定 Provider SHA256 `438178cb8e3575b9172cb98f5df3ee84a5ec20874840c8af8ccf0dab4856a4dd`；33条 evaluation 源 before=after；freshprocess `backend_modules=[]`。新证据 `evidence/qa/T26-evaluation-20261002T164628071232Z/result.json` raw `581a3c63cff1bf98b8df79343195192680eba433cb318c8ded4937a16492dcf9`，同目录 `process-result.json` 和 `unknown/*-result.json`。本次 QA 修正了两个真实 harness 错误（不强求出现源raw mismatch；合成批准ID格式），没有改变冻结 K1–K6 输入、预期、产品源码或预算。

真实网络/付费 0，原账本与凭据未访问，无超支结论；原始三scope失败保留。

后续 EVAL-002 修复后的完整独立 QA 亦已通过，真实exit0、193项/0失败、全10种未知/预留矩阵及settled对照再次通过；本 Finding 保持关闭。新证据 `evidence/qa/T26-evaluation-20261002T165331450690Z/result.json` raw `1e266bf8ede64966e0c9df892d785ee305a660b83edaa18ddac11f2b6004680e`。完整范围与限制见 [T26-acceptance-20261003.md](T26-acceptance-20261003.md)。
