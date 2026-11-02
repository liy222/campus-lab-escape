# 三笔未知调用保守核账与受控评价恢复（2026-11-02）

用户选择保守核账方向并要求开始。基线c20dffd。三笔game未知记录的完整预留/已计入上界0.027760+0.027760+0.055096=0.110616元继续保留；不核定供应商账单、不恢复HTTP回包、不把NULL token改0、不重发历史请求。

## 文件归属与实现

- Budget Owner临时拥有新scripts/reconcile_v5_unknowns.py：固定项目/三精确原记录，纯函数可接内存SQLite；默认只读dry-run，实际apply还需Main固定位置的具体批准记录。仅三目标state/reason可变，全部金额/NULL token/其他行/配置不变，完整事务与失败回滚，已全部闭合后重复无写入。原T27工具只读参考不复用旧人工费用陈述。
- Evaluator Owner临时拥有evaluation/v5.py付费接入逻辑（不改注册pin或INSTALLATION_PINS）及新scripts/preview_v5_evaluation.py。复用ExistingLedger/PaidProvider/validate_gate，不改provider/engine/reader。实际付费必须先证据READY，再校验固定Main有限授权及当前代码/登记绑定；全scope unknown/reserved、frozen/cap仍阻断，凭据必须在这些条件后读取。缺批准永不默认调用。异常/身份变化/新未知停止余项、0自动重试，准确记录实际attempt。
- QA仅新tests/v5/test_unknown_reconciliation.py、test_paid_recovery.py及本阶段结果/qa.md；Owner稳定后一次必要隔离验证，不跑旧全套或C1-C3产品节点、不build/浏览器/真实模型，不用玩家库测试。
- Main拥有本计划、AGENTS/根进度、固定证据、实际只读dry-run与免费preview、最终可信授权/登记元数据及Git。运行隔离检查与预检后集中提交推送，再把具体差异交本人确认；本轮不执行真实账本apply或任何真实评价。

## 核账约束

固定三条id/scope/创建时间/原reason/reserved/charged/NULL token须精确匹配；未知或在途集合不可夹入其他未处理请求。无新表/初始化/清空/迁移/释放预留；配置cap=原10元且未冻结。事务前后逐行全字段对比，除三目标state/reason外零变化；金额总计、行数和配置保持。临时/内存负例覆盖触发器/更新中断/额外未知/漂移/幂等，原账本只做查询。

## 受控评价与预检

三个有限Claim范围不变；既有71-source/9-evidence登记继续匹配，当前Backend不变。受信付费绑定须覆盖当前登记与评价代码/配置身份，不能只凭过期gate或任意CLI路径。授权文件由Main按实际用户批准写入，保留原授权和失效状态。max_calls/金额/输出/超时都是有限值，原共享CNY10 cap不提高。

免费预览只读取当前已注册证据并构造实际model messages，记录精确wire身份、三项费用上界、固定model/token/timeout、源码/登记绑定；用明确Synthetic预览输出，不冒充模型判读、不读Key/不预留预算/不发HTTP。新增真实调用次数/总额须由实际预检得出后另获有限批准；选保守方向或完成接管均不授予付费。

## 本轮完成条件

工具和恢复入口通过一次独立必要隔离QA；原账本dry-run完整差异可审阅，当前71源/证据身份仍匹配；未真实改账/调用，旧记录和安装固定项保持。给出具体apply和后续有限付费的待确认事项，不把准备就绪写成核账已完成或语义PASS。证据持续存于evidence/project/stages/v5-conservative-recovery。

## 实际交付

必要隔离验证及各一次真实只读dry-run/免费preview已完成，实际命令、失败夹具与窄补、三笔具体差异及最多3次/0.40元提案见[固定交付报告](../evidence/project/stages/v5-conservative-recovery/reviews/delivery.md)。真实账本apply及真实评价均未授权或执行。

## 具体批准后的实际执行

本人已批准核账及3次/0.40元，实际apply和三项真实评价均exit0，C1-C3全部PASS、用量估算0.02607224元，无新增unknown或重试。三次额度用尽；前文“只准备/未授权”是e4bf70b提案阶段范围，后续具体批准和实际结果以[执行报告](../evidence/project/stages/v5-conservative-recovery/reviews/execution.md)为准。
