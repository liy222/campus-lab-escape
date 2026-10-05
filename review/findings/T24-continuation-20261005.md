# T24 独立 E1 49 单元续跑执行器 QA

结论：稳定候选独立离线复核通过，无未闭合实现 Finding。本次不产生真实 E1 续跑结果或新的 Main 付费授权；HTTP、费用账本、授权与凭据失败均为明确合成数据。固定归档 v1 判断器在隔离子进程真实运行，parent 仅使用 canonical Provider/budget 的 fake transport/fake SQLite，不导入或执行当前 v2 domain。真实 `.env` 没有读取；原共享账本只计算原文件哈希，没有作为 SQLite 打开或写入。

## 实际运行

```text
C:\Users\liyh\.conda\envs\1\python.exe -B -X utf8 tests/review_e1_continuation.py --output evidence/qa/T24-continuation-20261005T113100Z
```

工作目录 `D:\深度能力`，actual exit 0，session 23159，chunks fa2c6d/ef1516：449/449 独立检查通过。先前 393/393 初轮也实际 exit 0（session 99080，完成 chunk b4100e），证据 `evidence/qa/T24-continuation-20261005T112300Z` 保留；为补齐 Main handoff/49 份已保存输入副本以及 CLI 凭据加载顺序，扩大 QA 后完整复跑。没有把 Owner 的 221 项结果算成独立结果，也没有重跑 Owner 测试。Owner 原两轮失败和其后通过记录原样保持。

## 独立结果与反例

冻结计划与重建计划完全相等，恰好原顺序 24–72 的 49 单元（full_history 24、structured_summary 25），reservation 合计 5,299,680,000 units。原 22 completed 与 1 timeout 全部排除。逐输入比较消息与 tools 原值相等、实际 HTTP 请求原始字节及长度精确一致；1000 tokens、20 秒、thinking disabled、tool_choice none，temperature/seed 不发送。49 份新计划输入副本与原输入原始字节哈希相等；消息/role/tool/计划 source、alias、row order、input hash 篡改均不能继续有效执行。

固定 v1 worker 真正重判原 22 completed，legal/correct/reference/next_action 结果逐条与原始结果相等。实测 LEVEL_VERSION 1.0.0、四个关键导入路径在固定归档内、依赖原始哈希绑定、v1 保留 emergency_key 的内存语义探针有效、未导入 archive Provider/budget。父进程禁止当前 v2 domain/API/storage 导入。worker 的 sample 路径、额外输入字段、非字符串、空批次、超长文本及超过 72 单元输入均被拒绝；注入指令文本保持数据，不执行网络、读取环境文件或执行 Provider。worker 审阅确认固定 allowlist、禁止 write/socket/subprocess；验证不表示一般自然语言安全能力。

隔离 fake HTTP 的 49 请求按原顺序各一次，逐次在传输前看到已保存 invocation_started journal 与正确 input hash，且 HTTP wire 是原始完整字节。missing usage 与 timeout 均一请求后停止、其余 not_called、usage NULL 与完整 reservation upper 保留；wrong reported model 一请求后停止。独立好/坏交替反例 `bad, good, bad, bad` 在第 4 次请求后停止，验证计数在成功后重置、两次连续已知费用解析失败停止。已有 unknown/reserved、阶段额度不足及 source assertion drift 在任何传输前停止。

已知费用返回后的模拟崩溃仅保留 pre-call journal、没有 raw/completion；只读恢复没有重发，fake DB 原字节不变。known、settled tokens NULL、多个候选 call 的三类快照分别保留已知 usage、未知 usage、未知 attempt；恢复不会把 NULL token 当零，不声称收到上游响应。原 origin 或 authorization id 已登记时拒绝重放。CLI 合成测试证明拒绝 admission 时 credential loader 未调用、未写 receipt；模拟已接纳 admission 后，凭据失败前已保存消耗记录，未构造 Provider 或发送请求。该合成目录有 QA-SYNTHETIC-FIXTURE.json，绝非真实授权或真实调用。

merge 实测 72 个原 row_id 与 lineage，原 23 个已尝试单元逐对象保持，结果为 71 completed + 1 原 timeout，两个变体 planned 分母仍 36。原 timeout call id `520a5c50b9204960a3f9915952ed9b97`、response/usage NULL、0.16292 full upper 均保留，不用人工陈述 0.05 重写实验字段或补判。duplicate/Git commit/input hash/order/variant/任意 filename 篡改拒绝；synthetic 输出默认不能作为 real merge。分批时间/cache/暂停/顺序连续性已改变，旧 latency 与新隔离判断开销混合，不能宣称变体优越、72 次完成或一般模型质量。

gate 合成反例覆盖完整 plan/freeze/original plan/selected identities/新五源/archive/baseline/dependencies hash、布尔/超限 max_calls、超额 cap、未批准 QA/closure、越界或错区域证据、到期/future/stale pricing、全局 cap/frozen/剩余额度及 unknown/reserved。canonical parent Provider/budget 文件路径和原 ledger 常量一致；读取原 ledger 的实现使用 mode=ro，QA 只对隔离 SQLite 执行此读取。正式 CLI 只有 real 分支的一处环境 loader，admission 和所有前置审查先于它。该分支仅在替换 admission/账本读取/凭据 loader 的合成函数测试中运行；没有绕过现有审批或进行真实授权执行/child HTTP。

## 源、证据与限制

Owner fixed handoff `experiments/runs/20261005T110033349203Z-continuation-plan-50250a53/owner-candidate-report.json` 原始 SHA256 `234f875816910ebdb21e79e1f1f8dc0d822f27470f36df063bc479ca77946921`。executor `247414c3c03c71395540725f9017fcf7a5686df21fade12a3da73eedf82cbecd`，worker `c9a0988ea7fc63c34300f4eaf2b77603b065af6dd6ba01ada1b1d8cd5dcb0224`。全部五份实现/文档/schema/test 源等于已保存计划 pins 且 before/after 相等；原 41 源、101 归档、原 run/plan/raw/journal/completion/summary、原输入、新计划及原共享 ledger 原始字节前后相等。

新增 QA 文件：`tests/review_e1_continuation.py`、本报告与两个 `evidence/qa/T24-continuation-*` 新目录。最终证据根 `evidence/qa/T24-continuation-20261005T113100Z` 含 `checks.json`、`result.json`、`process-result.json`、`historical-v1-judge.json`、`wire-observations.json`、`scenario-snapshots.json`、`counterexamples.json`、合成 run/journal/raw/recovery/merge、`source-stop.json`、`artifact-sha256.json`。假 SQLite 在导出合成快照后清理，最终无 `.sqlite`/`.env` 文件。源 STOP 给出完整实现与保护文件哈希，索引覆盖证据原始字节（不自引用）。原报告 sys.argv 没有解释器 flags，process-result 保留实际调用 `-B -X utf8`。

证据整理命令 `C:\Users\liyh\.conda\envs\1\python.exe -B -X utf8 evidence/qa/T24-continuation-20261005T113100Z/finalize.py` 实际 exit 0/chunk c4e5f9，索引 879 文件。最终原始 SHA256：result `4d9a25587db93ec25976c4bcfeb02f244284660aa506bc598f8195faed33d534`；process `ec8d8c2d53e70d10109cbf490ba9232f39018f2f747866f35f1c4cc810183f10`；source-stop `f1bcaa1072e79e5b7535ac4c6d00cd0b772531a92f52e43b78140a9e411f9b0a`；artifact-index `0936ee6f818144aebb636fbaffc41ee3f879913465e198e885d50c1f1b3da75b`；QA harness `a55cfab2c97a74b3f1cb4ac346d0fe6b182f16a41319386ee51c68920f6144b0`。

仅验证本次有限协议和冻结输入；没有凭据有效性、供应商账单、真实 49 次结果或独立人类验收证明。任何真实执行仍须经过单独的明确 Main gate 和自动审批。本次已 SOURCE STOP。
