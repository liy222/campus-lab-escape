# T27 首批真实校准结果独立只读复核

结论：报告解释与证据链最终独立检查 46/46 通过；真实校准运行本身 exit 1，11 案例仅 10 个匹配，不是完整校准成功，也不是 3 次真实调用完成。实际只有 2 个原 gate 付费尝试（账本/报告两个 call id）；本 QA 没有调用模型或修改会计状态。

最终实际命令：

```text
C:\Users\liyh\.conda\envs\1\python.exe -B -X utf8 tests/review_final_delivery.py --mode calibration --output evidence/qa/T27-calibration-20261005T160500Z --ledger-snapshot evidence/qa/T27-calibration-20261005T123100Z/calibration-review.json
```

工作目录 `D:\深度能力`，actual exit 0/chunk 293a4d，46/46。最终只用首轮捕获的 ledger epoch，没有重新打开 live ledger。Main 实际 paid process exit1/chunk c87825，source14 before==after，与当前实际源原始 SHA 相等；run report exit1/actual_paid_calls2，gate 是 max3/.22CNY/1000tokens/20秒、冻结 fixture hash，不从批准 3 推断实际调用 3。

K1-real-valid-evidence 的真实模型建议违反引用约束，validation error MODEL_FAKE_OR_UNREAD_REFERENCE，最终 INSUFFICIENT_EVIDENCE。无效模型原文本/raw_suggestion 不保存，只有 SHA `f1291d5beb8de72442f9d380c1715649b3fb8d5f643d6225e9cc333f65955c26` 与 1768-byte 元数据；没有 reflection/raw_content。最终输出保留的六个 evidence refs 与冻结 case 已登记并读取的六项完全相等，不是把模型虚假引用反射到结果。用量已知：prompt3694/completion453/cachehit0，charged11,012,000 units，call `eval_K1K6-20261005T110203Z_1` settled。

K2-explicit-failure 实际付费尝试 `eval_K1K6-20261005T110203Z_2` 遭 MODEL_UNAVAILABLE、usage NULL、full upper51,528,000。最终 FAIL 来自显式 NONZERO_EXIT/ASSERTION_FAILURE 的确定性证据，不代表成功语义模型判断。K4-failure-with-injection 因 PRIOR_CALL_UNKNOWN_STOP 未发起原 gate 请求，provider metadata/raw_suggestion 均 NULL；最终 FAIL 仍来自已存在确定性失败。不能把 K2/K4 的 FAIL 计成两次成功付费语义校准，不能自动补打或重发 K1/K2。

11 个冻结 case id 与 expected 全部核对；10 matches，falsePASS=[]、wrong_failure=[]，K1 为唯一 unnecessary abstention。其余分支的确定性放弃/批准 N/A 不生成额外付费记录。invalid raw 只有 digest/null，原 zero-paid 两份独立 QA 证据另列原始哈希保持，不能倒写成这次真实校准。

首轮 `T27-calibration-20261005T123100Z` actual exit1/chunk b05e62，42/45；三条失败真实保留：QA 错误要求 K1 abstain 时引用为空（实际合法读过 refs 可以保留）；另两项沿用任务卡 unknown/pending1，实际账本已由 Main 后续会计核清为 settled。并非模型错误被改掉或原报告重判。仅修正 QA 解释，first result/readonly snapshot 原样保存。

运行时历史 MODEL_UNAVAILABLE/NULL 不改；后续 Main full-upper apply 依据用户明确“不需要花费额外精力管费用，减少不必要的token花费，继续”，实际 exit0/fd360d。只闭合会计 hold 为 USER_FULL_UPPER_ACCOUNTED，保留完整51,528,000、NULL tokens，不填写 supplier actual fee（human_reported_cost_units NULL），不声称供应商 invoice 或恢复 usage。首轮实际 RO 捕获的 epoch 为85settled、total511,501,840（0.51150184CNY）、cap10/frozen0；QA 只核对两个校准 rows 和 aggregate，其他84完整 tuple 不变的全事务检查是 Main helper 的事实，不冒称本 QA 有其独立先前全表快照。

随后 Main 已分别获准另六 payload；本报告不读取其 ledger、不审查其结果、不把原85 epoch投射成未来当前账本，也不把 K4 先前未调用投射成后来调用。后六结果须另行独立交接。

实际原 report SHA `40aec88adcea8da225bcc439c98540701bf5b082f24046f7d32e4df7c0a67032`；Main paid process `b7d581ad32a96ebb15ff5142a7c5a16788dd1e0f28f02ba656df4b4ac2aef46e`；后续 full-upper applied record `e177c1c12271bcbd15a30c8dea6ce5d512e2bcd451e00687fbe88b6da9f512a1`。最终 result SHA `ccdb224d1604e478bd68a8fbe0ec6bb440dc3945e6ed03cbfb00cc36db914907`，旧captured snapshot SHA `4c315f05854c0e7367f88722aefd6e93122c4c0d71d7d7ef7f727cb6463f37cf`。

新增 `tests/review_final_delivery.py`、本报告、`evidence/qa/T27-calibration-*`。最终保存 checks/result/calibration-review/process/source-stop/index；所有原历史报告与代码只读，不运行 Provider、网络、.env、Git 或 apply。没有一般语言鲁棒性、真实独立人类判断、完整校准验收或追加调用授权。SOURCE STOP。
