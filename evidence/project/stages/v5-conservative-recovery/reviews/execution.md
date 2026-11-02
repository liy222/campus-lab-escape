# 保守核账与有限真实评价：执行结果（2026-11-02）

本人明确批准“批准核账及3次评价／0.40元（推荐）”后，Main按已推送e4bf70b的具体提案完成执行。授权原话、原问题和导入时间见[本人记录](../../../human-reviews/v5-conservative-recovery/round-01/review.md)；该批准不是本轮结果的真人验收。当前为技术完成、待本人核对结果。

## 结果

| 项目 | 实际结果 | 原始证据 |
|---|---|---|
| 三笔历史记录核账 | apply exit0；仅state/reason变化，完整0.110616元上界、原reserved/charged和NULL用量保留；其他行/表/配置不变 | [apply原件](../runs/20261102T114636930048Z-2ecb52918a60/result.json) · [批准绑定](../reconciliation-approval.json) |
| V5-C1：有限生成/拒绝规则证据 | PASS；判读已有9个准入/EXIT回放及20坏例拒绝证据 | [真实评价报告](../evaluation/paid-20261102T114835067721Z-d8ca9df3/report.json) |
| V5-C2：跨账号私有资源隔离证据 | PASS；判读已有11个越权请求拒绝且状态不变证据 | 同上 |
| V5-C3：定义/三时刻恢复/坏档保护证据 | PASS；判读已有三时刻定义/状态一致和坏checksum拒绝证据 | 同上 |
| 次数和费用 | 3次真实调用，固定Claim各一次，无重试；按返回用量和锁定峰值费率估算0.02607224元，低于0.40元批准限额；不是供应商账单 | [执行入口记录](../evaluation/execution-v5-claims-20261102T114624Z.json) · [执行后只读账本](../logs/after-execution-readonly.json) |

三次授权名额已用尽，不结转、不追加。账本现在178条settled、unknown0/reserved0、未冻结；原10元cap不变，本地累计计入上界1.34807592元。历史三笔闭合是本人接受完整上界的核账处理，实际供应商用量仍未知，不能将NULL写成0或声称核实旧账单。

## 范围与执行事实

评价使用当前71源/9证据可信登记，读取前阶段实际产品观察，不重跑产品或重新生成关卡。三项请求体字节/hash与已批准免费预览相同；当前登记/20项评价来源绑定和源码前后相同，precheck与final precheck均READY/issues[]，三项引用重新读取校验通过，audits的validation_errors均为空。请求/响应model均为既有deepseek-flash，finish_reason均stop，没有扩充allowlist、安装pin或合同。

凭据仅在当前证据、固定有限批准、账本全scope就绪及本gate未使用均通过后读取。复用项目现有DeepSeekConfig读取MODEL_API_KEY，仅注入本次子进程的EVALUATION_MODEL_API_KEY；固定provider/model/URL保持，不在命令参数、日志、证据或Git保存Key。没有更改.env或玩家数据库。既有Provider负责原子预留和返回用量入账，执行后Main另作只读查询，没有新调用。

实际核账命令exit0：

```powershell
& 'C:\Users\liyh\.conda\envs\1\python.exe' -B -X utf8 scripts/reconcile_v5_unknowns.py --apply --operator Main
```

唯一真实评价子进程exit0：

```powershell
& 'C:\Users\liyh\.conda\envs\1\python.exe' -B -X utf8 -m evaluation.cli evaluate --release v5.0-engineering --mode paid --approval-id v5-claims-20261102T114624Z
```

这一次支付评价不是再做一次产品pytest。没有build/浏览器/原全套/C1-C3产品四节点重跑/生成/伙伴/校准/自动重试。14项核账及28项paid入口隔离结果及检查器非零记录仍按前轮[QA报告](qa.md)保留，不计成本次新测试。执行结果独立只读复核见[execution-review.md](execution-review.md)，不重复真实调用。

## 本人核对入口和限制

请本人检查本页三项结果、三笔旧金额保留和本次0.02607224元估算是否符合批准范围；无需重测游戏或再提供Key。本次没有UI改动或可对应的截图，未补造截图。结果接受保持待本人反馈。

三个PASS只针对登记的有限C1-C3工程证据，不代表五主题美术/AI自然度/普遍成功率、全站安全认证、所有结构及所有后续源码已经通过。原确定性IE和旧未知阻断记录按历史时点保留，不改写为旧时已PASS。本人接管已按真实原话完成；同伴/教师签字、整版发布接受、tag、合并main、部署和Actions没有发生。
