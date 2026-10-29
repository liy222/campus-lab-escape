# 项目证据固定入口

今后从这里读取、整理和提交证据。开发中每次实际检查、失败、修复和反馈及时保存，大阶段结束再集中交付并邀请真人核验。

## 当前阶段：手绘重建、UI修复与电脑端清理

2026-10-29追加HP-01名称点击修复：[真实反馈round-01](human-reviews/v5-handpainted-rebuild/round-01/review.md)、[独立检查](stages/v5-handpainted-rebuild/reviews/hotspot-pointer.md)、[修复后本人复验round-02](human-reviews/v5-handpainted-rebuild/round-02/review.md)。鼠标按下动效覆盖居中已修复，实际游戏定向联合通过；本人尚未复验。

- [本阶段交付摘要](stages/v5-handpainted-rebuild/reviews/delivery.md)：4项UI修复、15张实际手绘原图、经典/V5电脑端范围；技术联合检查通过，待本人检查。
- [手绘/UI独立QA](stages/v5-handpainted-rebuild/reviews/qa.md)、[电脑端构建](stages/v5-handpainted-rebuild/automated/desktop-cleanup-build1/result.json)、[最终桌面窄补](stages/v5-handpainted-rebuild/automated/desktop-smoke-2026-10-29T05-41-37-562Z-adadb34b/result.json)。各轮范围分开，原失败保留。
- [阶段状态](stages/v5-handpainted-rebuild/stage.json)与[本人检查步骤](human-reviews/v5-handpainted-rebuild/round-02/review.md)：round-01实际点击问题已记录为需修改，修复后的round-02尚未收到反馈，未登记接受。
- [新版桌面实际截图](stages/v5-handpainted-rebuild/automated/desktop-smoke-2026-10-29T05-41-37-562Z-adadb34b/v5-desktop-1280.png)、[第三房间实际截图](stages/v5-handpainted-rebuild/automated/browser-2026-10-29T05-06-00-985Z-3c2b8e97/theme-G3.png)。均为自动截图，不冒充本人截图。

## 前一主题/UI来源

[74eb523来源的独立检查](stages/v5-rainy-astronomy-ui/reviews/root-review-20261029.md)实际复现4项问题，原10项结果、旧截图和原阶段状态保留。修复结论以当前新阶段为准，不将旧失败改为通过。手机相关原始证据保留为旧版本事实，现行实现与测试不再包含手机专用路径。

## 此前E&O阶段

- [本阶段结果摘要](stages/2026-10-28-evaluation-observability/evaluation/summary.json)
- [评价标准与评价器说明](stages/2026-10-28-evaluation-observability/evaluation/evaluator-status.md)
- [Evaluation与Observability阶段记录](stages/2026-10-28-evaluation-observability/stage.json)
- [两种输入的实际生成过程](stages/2026-10-28-evaluation-observability/logs/two-input-generation-traces.json)
- [浏览器的预期和实际值](stages/2026-10-28-evaluation-observability/automated/browser-run1/browser-result.json)
- [重登录窄补结果](stages/2026-10-28-evaluation-observability/automated/browser-auth-finish1/browser-result.json)
- [独立复核说明](stages/2026-10-28-evaluation-observability/reviews/qa.md)
- [本阶段真人检查表](human-reviews/2026-10-28-evaluation-observability/round-01/review.md)

本人已提交[本轮实际试玩反馈和原截图](human-reviews/2026-10-28-evaluation-observability/round-01/review.md)：生成、通关、注册、登录正常；UI简陋、主题画面不符、素材不足，状态为需改进。E&O证据条目和真实同伴仍未确认，整体未接受。技术结果摘要保留编写时状态，最新真人结论以阶段元数据和真人记录为准。

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
