# 保守核账与评价恢复：准备交付（2026-11-02）

后续实际执行已完成，见[最新核账与三项真实PASS结果](execution.md)。以下保留e4bf70b准备交付时点的提案与“尚未批准”状态，不代表后续批准/执行尚未发生。

基线c20dffd。本人已确认接管操作全部成功及程序/AI/存档职责理解，[原话](../../../human-reviews/v5-current-evaluation/round-01/review.md)按实际范围保存。本阶段工具及入口已完成必要独立隔离验证，并做了各一次只读账本预演和免费请求预览；**真实账本未改，真实评价未运行，也没有本轮apply或付费批准**。

## 本人核对的具体变更

[只读预演原件](../runs/20261102T113622500889Z-4ea33b806f6f/result.json)标记PROPOSED_NOT_APPLIED；实际before与after及完整内容指纹一致。175条记录，已计入上界1.322003680元，cap仍10元、未冻结；这些是本地上界记账，不是供应商账单。

| 三笔历史记录 | 原原因 | 已计入且继续保留的上界 |
|---|---|---:|
| e0ed1e09d56c43fe99cf554ee98cb8d3 | INTERRUPTED_OR_INTERNAL | 0.027760元 |
| d717f047d96542f0b391c7a50f47f994 | MODEL_AUTH_ERROR | 0.027760元 |
| d6b0528c32c048efa845e5ae813001b2 | MODEL_AUTH_ERROR | 0.055096元 |

拟仅将这三条state由unknown改为settled，reason改为HUMAN_ACCEPTED_UPPER_RETAINED，明确为本人接受完整上界的核账闭合。合计0.110616元不减少，reserved/charged、创建时间、scope、三个NULL token字段、其他行/表/配置不改；原失败原因在预演before和历史原证据中保留。不把未知实际用量写成0，不推断供应商扣费或重发旧请求。改账本身不产生新模型调用。当前默认只读；缺少固定、来源绑定、未过期的具体批准时，CLI在打开可写账本前拒绝。

## 后续真实评价的有限预算提案

[免费请求预览](../evaluation/preview-20261102T113731971881Z-e6d252b2/preview.json)准确捕获当前Evaluator三份消息及最终请求体身份，无Key/ledger/HTTP访问，Synthetic捕获回复不是模型判断。仍用deepseek-flash，单项最多1000输出token/20秒，无重试。

| 固定评价范围 | 请求体UTF-8字节 | 费用保守上界 |
|---|---:|---:|
| V5-C1 | 16476 | 0.156192元 |
| V5-C2 | 11660 | 0.117664元 |
| V5-C3 | 10590 | 0.109104元 |

三项合计上界**0.382960元**，建议有限批准为**最多3次、总额不超过0.40元**，每Claim一次、失败占次数、不重试；异常/IE/新unknown即停余项，不调用生成、伙伴或校准。它是新增费用提案，不是已发生费用。峰值费率与[公开来源说明](provider-pricing.md)相符；共享10元cap不提高。

恢复入口已取代原paid无条件停止逻辑，改为检查当前证据/登记和评价来源、固定Main有限批准及全scope账本就绪；任何unknown/reserved、冻结、超额或来源变化仍阻断，Key读取后置。账本闭合不自动授予付费；缺Key则本地停止。本轮未验证实际凭据存在性，不保证未来模型给出PASS。合法FAIL保留，错误或缺证停止余项，真实attempt计数和后续报告写固定阶段。

## 实际验证、命令与证据

独立[QA报告](qa.md)：核账14项在首轮合并exit1中全部通过，失败来自新paid测试夹具；只修夹具并窄补paid文件，最终28 passed/exit0、既有warning1。原非零结果全部保存，不能拼成一次全绿；没有产品实现缺陷被这组有限检查发现，也没有重跑既有四个C1-C3产品节点。Owner开发替身检查单列在[开发记录](evaluator-development.md)，不冒充独立QA。

Main在上述核账范围独立通过后只执行一次默认只读预演（exit0），paid范围稳定后执行一次免费预览（exit0）：

```powershell
& 'C:\Users\liyh\.conda\envs\1\python.exe' -B -X utf8 scripts/reconcile_v5_unknowns.py --operator Main
& 'C:\Users\liyh\.conda\envs\1\python.exe' -B -X utf8 scripts/preview_v5_evaluation.py
```

本轮没有build、浏览器、旧全套、产品C1-C3重跑、真实模型或付费调用，没有读取玩家数据库/私有原稿/Key，未改原provider/engine/reader/CLI、注册pin或16项安装固定项。71份产品来源保持原登记范围；免费预览的READY/完整覆盖不是语义PASS。

## 请本人检查及下一步

请核对上表三笔金额保持和仅state/reason变更，再看三项评价总额0.382960元是否同意。可以只批准核账，也可以同时批准核账与最多3次/0.40元真实评价；两项都尚未执行。本轮没有新游戏画面，检查入口是本页及两份实际预演JSON，不要求重新游玩或生成关卡。整体发布、同伴/教师签字和语义评价结果仍按实际未发生项保留。
