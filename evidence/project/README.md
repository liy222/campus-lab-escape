# 项目证据固定入口

今后从这里读取、整理和提交证据。开发中每次实际检查、失败、修复和反馈及时保存，大阶段结束再集中交付并邀请真人核验。

## 当前阶段

- [本阶段结果摘要](stages/2026-10-28-evaluation-observability/evaluation/summary.json)
- [评价标准与评价器说明](stages/2026-10-28-evaluation-observability/evaluation/evaluator-status.md)
- [Evaluation与Observability阶段记录](stages/2026-10-28-evaluation-observability/stage.json)
- [两种输入的实际生成过程](stages/2026-10-28-evaluation-observability/logs/two-input-generation-traces.json)
- [浏览器的预期和实际值](stages/2026-10-28-evaluation-observability/automated/browser-run1/browser-result.json)
- [重登录窄补结果](stages/2026-10-28-evaluation-observability/automated/browser-auth-finish1/browser-result.json)
- [独立复核说明](stages/2026-10-28-evaluation-observability/reviews/qa.md)
- [本阶段真人检查表](human-reviews/2026-10-28-evaluation-observability/round-01/review.md)

真人状态保持未核验，直到收到本人实际反馈。技术检查和真人结论分别记录。

## 目录怎样使用

```text
evidence/project/
  index.json                       当前阶段与阶段列表
  stages/<stage-id>/
    stage.json                     范围、技术状态、真人状态、归档来源
    automated/                     实际测试/浏览器结果及相应自动截图
    logs/                          可提交的安全日志导出
    evaluation/                    本阶段标准、评价结果与说明
    reviews/                       AI或独立技术复核
    screenshots/                   其他注明来源的阶段图片
  human-reviews/<stage-id>/round-XX/
    review.md                      便于阅读的当前轮核验记录
    events.jsonl                   逐条追加的真人反馈、来源和导入时间
    screenshots/                   该轮用户明确提供的原截图
```

原始生成日志仍在新版数据库的generation_job_events表，可用只读工具导出JSON归档到阶段logs/；数据库本身不挪入证据包。评价器程序保留代码位置，采用的标准、结果和版本说明在阶段evaluation/中。

## 真人检查与反馈

每个大阶段结束，代理给出体验入口、三到五项检查重点和已知限制。本人实际检查后，将通过/需修改/尚未核实的结论、操作过程和截图发回；代理按原话和真实来源归档。若需修改，同一阶段开下一轮，旧反馈和截图保留。

本人、同伴、自动化执行者分别标注。只有本人当前轮明确接受才登记为真人接受；只有截图、测试通过或创建核验表都不代表接受。原核验时间未知时保持空白，导入时间单独记录。

## 已有真人反馈

[生成关卡修复前的用户反馈与原截图](human-reviews/2026-10-28-generated-play-feedback/round-01/review.md)已纳入归档。它证明用户实际体验并提出问题，不能代替修复后的核验。

## 历史迁移与操作入口

[历史证据索引](HISTORY.md)列出已归档的旧证据和保留的原入口。归档保留原内容、来源和时间，不意味着重新执行。对固定路径引用的历史原件先保留兼容；新证据直接写入此处。

归档命令见[使用说明](../../docs/v5-evaluation.md)。源码入口：[证据工具](../../scripts/evidence_hub.py)、[日志只读导出](../../scripts/generation_trace.py)、[原工程评价器说明](../../evaluation/v5/README.md)。密钥、数据库和私有原稿不属于可提交证据。
