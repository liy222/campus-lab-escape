# T22-EXP-001（P2）：上游响应三态记录

首轮独立复现，待修复稳定后复测。详细原始 Finding：[T22-experiments-finding-20261002.md](T22-experiments-finding-20261002.md)。

独立命令 `C:\Users\liyh\.conda\envs\1\python.exe -B -X utf8 -m tests.review_e1 --transport-only` 实际 exit1；43 断言中 12 失败。证据 `evidence/qa/T22-experiments-20261002T124810497454Z/result.json` 及 `transport/transport-results.json`，源 before=after。

Frozen DeepSeekProvider + MockTransport + QA 自有 fake ledger：401/403/429/503/malformed200 均实际收到 HTTP，却 response_received=false、upstream_delivery_known=null；ConnectError/ReadTimeout 响应未知却写 false。summary 缺少响应未知数。无网络/付费/凭据/原 ledger 访问，失败无重打，调用前 journal 与实际输入 hash 通过。

修复仅在 experiments 层安全观察 HTTP，并将确证响应、未调用、调用后未知分别记录 true/false/null；汇总保留确证下界和未知数。禁止修改 frozen Provider 或用 metadata 冒充 HTTP 已收到事实。全部首轮事实保留，不预填修复结果。

## 2026-10-03 独立复测关闭

状态：**关闭**。稳定候选完整独立复测真实 exit0，764 项全部通过，83 条源记录 before=after、完成后当前源也全部匹配。命令 `C:\Users\liyh\.conda\envs\1\python.exe -B -X utf8 -m tests.review_e1`；新证据 `evidence/qa/T22-experiments-20261002T164754631028Z/result.json` 与同目录 `process-result.json`。raw result SHA256 `54d730377941179358ee439d73f1214fbdcbb634d2a628f2ba41e43fd303587b`。原首轮失败及既有完整通过保留，具体覆盖与局限见 [T22-acceptance-20261003.md](T22-acceptance-20261003.md)。真实网络/付费 0，未访问真实凭据或原生产账本；不是 E1 真实调用验收。
