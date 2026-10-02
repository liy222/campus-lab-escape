# T22-EXP-001 — 响应确定性记录错误（P2）

状态：2026-10-02 首轮独立复现，待 Owner 修复后稳定复测。Main 提供的是待验证线索；以下为 QA 自己执行结果。

`experiments/runner.py` 的 `execute` 将 `ProviderError` 的 `response_received` 写为 `bool(last_response_metadata)`。冻结 Provider 的 metadata 指标准化回复诊断，不能作为是否已收到 HTTP 响应的依据。

独立最小反例采用当前冻结 `DeepSeekProvider`、`httpx.MockTransport` 与 QA 自有临时 SQLite 账本，分别返回 HTTP 401/403/429/503、格式错误的 HTTP 200，以及抛出 ConnectError/ReadTimeout。五个确实收到 HTTP 响应的场景均被记为 `response_received=false, upstream_delivery_known=null`；两个网络不确定场景均被记为 `response_received=false`，错误地把未知写成否。汇总只记录确证 `responses_received`，未给出未知响应数。

实际命令：`C:\Users\liyh\.conda\envs\1\python.exe -B -X utf8 -m tests.review_e1 --transport-only`；exit **1**，43 个断言，12 个失败。没有实际 Provider 网络、付费调用、凭据读取或原始共享账本访问；测试内部的 `mode=real` 仅配合明确替换的配置/Provider 工厂/ledger_read 验证真实分支逻辑。所有输出明确标注 synthetic。

证据：`evidence/qa/T22-experiments-20261002T124810497454Z/result.json`，同目录 `transport/transport-results.json` 及各场景 `runs/*/raw.jsonl`、journal、summary。生产/实验源 before/after 全部相同。各错误仅一次传输调用，剩余行保留 not_called，未重试；调用前 journal 和实际 payload hash 均通过。这是实验记录缺陷，不是冻结游戏代码失败。

修复要求：在 experiments 层区分“收到安全观察的 HTTP 响应”“明确尚未调用”“调用后响应/投递未知”，保留 true/false/null；标准化模型回复另行表示。汇总保留收到响应的确证下界及未知数。不修改冻结 Provider，不记录原始上游 body/header/secret。保留本轮失败证据，不用复测覆盖。
