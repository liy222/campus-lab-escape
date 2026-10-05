# T27 新 unavailable 请求保守核账独立 QA

结论：稳定 Main helper 的独立隔离测试 130/130 通过，无未闭合实现 Finding。本次只允许指定 unknown/MODEL_UNAVAILABLE 请求改变 state/reason，保留完整预留和所有 NULL token。用户的“0.09”是人工费用陈述，不是独立供应商账单、HTTP 回包或 token 恢复。本 QA 不运行原账本 apply、不发送请求。

## 实际执行

```text
C:\Users\liyh\.conda\envs\1\python.exe -B -X utf8 tests/review_unavailable_reconciliation.py --output evidence/qa/T27-unavailable-accounting-20261005T120700Z
```

工作目录 `D:\深度能力`，actual exit 0/chunk 5298c4，130/130。新 harness 从旧 QA 只读参考产生到新指定文件，并新增精确新 target、连续重复零 SQL 更新、他行多列同 aggregate 攻击；旧测试与 Main helper 都未修改。准备脚本 actual exit 0/chunk bed4f6。本轮没有失败测试或被掩盖的错误。

## 验证范围

精确请求 `6dfc591c79c54544afe6d70eec6d697b`，scope experiments、created_at `2026-10-05T11:49:17.549231+00:00`，reserved/charged 均 94,536,000 units，unknown/MODEL_UNAVAILABLE，prompt/completion/cache 三列 NULL。Main dryrun 的 helper 原始 pin 与当前新源码精确一致，其 before==after、费用人工陈述 90,000,000、full upper 94,536,000 均保留，未声称 known usage 或独立 invoice。

原共享账本仅 `mode=ro` 打开，独立捕获全部 83 行所有 10 列、config、状态汇总及 trigger 名。测试前后完整映射相等：82 settled + 1 unknown，charged upper 448,961,840 units（0.44896184 元），cap 10,000,000,000、frozen=0。这是真实 QA 执行期间的 preapply 快照，不在 Main 后续 apply 后复用为当前 unknown 结论。

所有 apply=True 测试仅在 SQLite `:memory:`。正例恰好改变目标 state 为 settled、reason 为 HUMAN_FEE_REPORTED_UPPER_RETAINED，83 行计数、full bound、total、cap/frozen/NULL tokens 与其他 82 行逐 tuple 保持；人工 0.09 不用来回收 0.004536 的预留差额。dryrun total_changes 不变，query_only dryrun 有效，query_only apply 被拒绝。已闭合状态重复 apply/dryrun 幂等，额外三次重复的 SQL total_changes 也不增加。

拒绝反例覆盖不同 id/scope/time/reserved/charged/state/reason、任一 token 由 NULL 变 0、缺目标、错误已闭合 reason、cap 增减、frozen、缺或额外 config、已超过全局 cap、其他 unknown/reserved、人工陈述超过 upper。update 被忽略、update ABORT、charge 回收、删除其他行、目标 token/cap/frozen/reason 改变、他行 scope/time/token/pending 改变、不同他行 charged 同总额交换、多列他行篡改均拒绝并精确 rollback，事务释放。模拟 commit exception 与 update 后 KeyboardInterrupt 也 rollback 到原样；没有靠只检查 count/SUM 来认定安全。

本 QA 从未调用 helper.main 或原 `--apply`，无真实环境文件、网络、付费请求、Git 或外部消息。原已验证 timeout helper、旧 dryrun/applied 人工费用记录以及原 formal raw/summary 当前字节前后相等；不改写原实验中的 unavailable、无回包、NULL usage 或旧 timeout 历史。未声称使用了独立可验证的运行时模型身份。

## 证据与停止边界

新 helper 原始 SHA256 `151b30144e1f440e3abb8c7901d3e27c180601d742fcfcb24f15d7e5989175b8`。新增文件只有 `tests/review_unavailable_reconciliation.py`、本报告及 `evidence/qa/T27-unavailable-accounting-*` 新目录。最终证据根 `evidence/qa/T27-unavailable-accounting-20261005T120700Z` 含 checks/cases/result/process-result/source-stop/artifact-sha256。cases 全为内存假账本；result 包含独立原账本 83 行 preapply 快照供 Main 实际 apply 后仅 state/reason 变化复核。索引保存证据原始哈希，不自引用。

证据整理实际命令 `C:\Users\liyh\.conda\envs\1\python.exe -B -X utf8 evidence/qa/T27-unavailable-accounting-20261005T120700Z/finalize.py`，exit 0/chunk 7f0ca7。原始 SHA256：result `29417daace840cf41bb35669e290d1f04f64690f27a05ede0417205e96066ead`；process `2f99d70481a0e0c704ba2f59e663a245724a8993af305622ecdb1f4f24a8d015`；source-stop `42512a8f6991165f0e95a2e980b1797817fb872688b1c959b28e22d2e8df91e8`；artifact-index `fbf2bd1809e7be179cfa93f3e6513b0ed8e356c6d877d4582a5088bb7683da17`；新 harness `de174d5ed17bb0efcdcec77f45b03d7792febcc02102bf20cc32fecf930fa113`。

130 项执行后停止原账本读取。本报告是 Main apply 前独立结论；apply 后另有 `T27-unavailable-accounting-postapply-20261005.md`，原 preapply result 与本报告历史快照不重写。source STOP 不授予其他真实调用或新增预算。人工费用仍不是独立 invoice，token/HTTP 不确定性不恢复。
