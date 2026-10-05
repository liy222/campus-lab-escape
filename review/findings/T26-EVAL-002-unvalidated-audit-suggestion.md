# T26-EVAL-002（P2）：未经输出 Schema 校验的模型字段进入审计

状态：独立 QA 最小反例已复现，等待 Evaluator Owner 修复稳定；不得以本次 178 个通过项宣称完整 T26 已通过。

版本：`evaluation/engine.py` 在本次 `result.json/source_before` 绑定的 SHA256；运行前后全部 evaluation 源一致。稳定预算修复 provider SHA256 `438178cb8e3575b9172cb98f5df3ee84a5ec20874840c8af8ccf0dab4856a4dd` 未修改。

前置与最小输入：受信 K1 的已登记 claim，`FakePaidProvider`、独立假账本、`httpx.MockTransport`；在原合成建议中仅加入额外 `api_key` 字段，其值为合成占位串。真实凭据没有被读取、传输或记录，QA 证据不保存该占位值。

预期：非法建议返回 `INSUFFICIENT_EVIDENCE`，保留类型/哈希/错误码等最小诊断；未知敏感字段不能进入可持久化 audit。

实际：最终输出确实是 `INSUFFICIENT_EVIDENCE`、错误 `MODEL_SCHEMA_OR_PROVIDER_ERROR`，但 `Evaluator.evaluate` 在 suggestion Schema 校验前赋值 `audit['raw_suggestion']=suggestion`。非法 `api_key` 及其合成值仍在返回 audit 内。本例只证明非法字段反射，未证明真实密钥泄露或付费请求。

真实命令：`C:\Users\liyh\.conda\envs\1\python.exe -B -X utf8 -m tests.review_evaluation`；进程 exit **1**，179 项断言中仅 `invalid_suggestion_no_secret_persisted` 失败。此前两个 harness 错误修正于 QA 文件（认可 raw identity 如实相等；合成 gate ID 的下划线改为连字符），未降低目标输出或引用校验要求。

证据：`evidence/qa/T26-evaluation-20261002T164628071232Z/result.json`（raw SHA256 `581a3c63cff1bf98b8df79343195192680eba433cb318c8ded4937a16492dcf9`）；`provider/unsafe-suggestion-result.json`（raw SHA256 `2f7da6d13022254add6e5b69c7c665fa7914ad8f2f38b049f58ad6e4803fd9d1`）。后者仅含输出、错误、字段名、哈希及布尔观测，未保存敏感值。

已通过范围：可信冻结与发布 pin、Windows 路径/ADS/设备名/junction 边界、四状态 K1–K6、假引用、证据注入、调用上限、错误与未知预留、所有 game/experiments/probe/同 gate 与异 gate evaluation 的 unknown/reserved 均在传输前拒绝并不追加行；settled 对照可追加一次假调用。`backend_modules=[]`；实际网络、付费调用均 0，原生产账本访问和凭据读取均 false。

Owner：Evaluator。建议最小修复是在 Schema 校验前仅存不可反射值的诊断元数据，验证后的合法建议按既有审计语义保留；需要保留 K4 的实际判读路径和合法审计字段，不改变冻结输入或预期。修复后交独立 QA 完整复测；本轮失败原始证据保持。

限制：未运行目标 backend、未做真实模型判读、无人类/教师签署；没有更改产品 v1、manifest 或生产账本。

## 2026-10-03 稳定修复独立关闭

状态：**关闭**。Owner stable engine raw SHA256 `14b8b6d4db9fd0d58d3748f1a9072710e26acfbf3f39f3493caa04311195ff6e`，完整 freshprocess 独立复测真实 exit0，193 项全部通过、34 条源 before=after，`backend_modules=[]`。证据 `evidence/qa/T26-evaluation-20261002T165331450690Z/result.json` raw `1e266bf8ede64966e0c9df892d785ee305a660b83edaa18ddac11f2b6004680e`，同目录 `process-result.json`。

原敏感字段反射断言现在通过；非法suggestion raw为空，只保留哈希、大小及通用错误，11类额外拒绝路径也未审计非法值。K4保留1次有效scripted judgement及raw PASS/final FAIL，未绕过判读。最小反例新证据 `provider/unsafe-suggestion-result.json` raw `d4ce866104cb2689077713f8591ad8a53345772a16ecb57f2ae70e87320d4206`；未保存合成secret值。旧失败保持。详见 [T26-acceptance-20261003.md](T26-acceptance-20261003.md)，其真实调用与人类签署局限仍适用。
