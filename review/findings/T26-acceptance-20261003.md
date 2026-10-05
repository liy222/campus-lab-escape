# T26 独立 QA 完整复测验收

结论：稳定 Evaluator 工程候选独立 QA **通过**，T26-EVAL-001 与 T26-EVAL-002 均关闭。未因此完成真实付费判读或人类签署。

真实命令：`C:\Users\liyh\.conda\envs\1\python.exe -B -X utf8 -m tests.review_evaluation`；实际进程 exit **0**（工具 chunk `c2c533`）。新证据 `evidence/qa/T26-evaluation-20261002T165331450690Z/result.json`：193 项、0 失败、34 条源记录 before=after；结束后再次核对当前源全部一致；freshprocess `backend_modules=[]`。同目录 `process-result.json` 保留真实命令及 exit，所有历史失败保留。

稳定 Owner 交接 `evaluation/handoff-T26-EVAL-002.json` raw SHA256 `c097a29378b310d6fbe431d9822a6e2477786dea25cb4b9232e1cb2f912590d2`，只作为修复候选依据，不将 Owner 114 项当独立验收。复测源 `evaluation/engine.py` = `14b8b6d4db9fd0d58d3748f1a9072710e26acfbf3f39f3493caa04311195ff6e`；`evaluation/provider.py` = `438178cb8e3575b9172cb98f5df3ee84a5ec20874840c8af8ccf0dab4856a4dd`；`evaluation/check.py` = `c7bedbe312c53d4d4fb3038d0e7330c09eeb9aaa530f6deaab26f481218367f8`。QA harness `tests/review_evaluation.py` = `3b7abdc78fa35c3956c546891a8169971f244e703898839e0473705269bea616`。

QA 修改范围仅 `tests/review_evaluation.py`：修正 raw identity 断言，使 raw 相等也如实通过且非raw相等仍要求 canonical 绑定；合成 gate ID 使用合法连字符；扩充共享未知矩阵到 game/experiments/probe/同 gate 与异 gate evaluation × unknown/reserved，检查错误、0 dispatch、0新行及旧行原样；增加 settled 对照；非法模型建议在所有11种 schema/文本/引用/状态拒绝路径中不进入 raw audit，并复核敏感字段反射的原断言、错误码与仅哈希/大小诊断。没有改变产品实现或冻结预期。

主要结果：Windows Reader 拒绝路径穿越、ADS、UNC/设备名、敏感路径和 junction，保持外部 sentinel；真实 raw/canonical 身份与 Main manifest/addendum pin 保留；28个 MUST 未被目标 N/A 自降；四状态11个 K1–K6固定输入均符合预期；假引用、跨release、未读snippet、错误hash、过期事实、重复引用、证据变化及注入均拒绝。K4 明确进入1次 scripted judgement，合法审计 raw status=PASS，确定性失败仍最终 FAIL。完整 CLI 的 precheck/mock 成功、deterministic 缺判读返回2、无有限GO paid模式在构造Provider前拒绝。

预算修复：10种全scope unknown/reserved场景均 `PRIOR_CALL_UNKNOWN_STOP`、传输与provider attempts 0、无新行、旧行不变；settled对照允许1次合成调用和1条新settled行。用量结算、重放冲突、错误与缺usage保守计入unknown、超限冻结、相同gate限次、共享cap及并发只预留一次均通过。

审计修复：额外敏感字段最小合成反例返回 `INSUFFICIENT_EVIDENCE` 和 `MODEL_SCHEMA_OR_PROVIDER_ERROR`，`raw_suggestion=null`、未知字段与合成值均不在输出/audit；只保留拒绝内容 SHA256 和字节数。QA证据也未保存合成敏感值。

证据 raw SHA256：完整 `result.json` = `1e266bf8ede64966e0c9df892d785ee305a660b83edaa18ddac11f2b6004680e`；`engine/independent-calibration.json` = `afd08252a6e1670892b062882da5aaf2ff1f1a042c606ec08341b2c74b0b42b1`；`provider/unsafe-suggestion-result.json` = `d4ce866104cb2689077713f8591ad8a53345772a16ecb57f2ae70e87320d4206`；`unknown/settled-control-result.json` = `fd0870fcb9e1f453258fcd528529df493d23840b6b1f40dd1b4243b40a00a8d5`。

未解决局限：仅固定工程范围与合成transport校准；模型真实判读、真实费用/自然模型抗注入、E1/E2/E3注册扩展尚未由本次验证。实际付费与网络调用0，原生产账本和凭据未读取，未导入/运行目标backend，不提供人类/教师签署；未用Agent校准代替真实课程审核。产品v1 manifest raw保持 `9c36943cbb6e4fe08b6e176445ba91835fafa79a2077c2155bbf8d613f8b07c1`，本角色未改Git或产品源码。
