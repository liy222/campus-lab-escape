# 项目证据固定入口

今后从这里读取、整理和提交证据。开发中每次实际检查、失败、修复和反馈及时保存，大阶段结束再集中交付并邀请真人核验。

## 当前阶段：临时API Key界面安全收尾

补当前界面的Key生命周期与允许传输范围，0真实模型/付费，复用未受影响后端证据。最终10条记录通过，42个API响应扫描完成、未读0，旧失败与检查器补强前结果按时点保留；本人已反馈“测试成功”，本次未附图，按授权复用原自动图作辅助；[真人反馈/辅助图源](human-reviews/v5-key-safety/round-01/review.md)。[交付与边界](stages/v5-key-safety/reviews/delivery.md) · [独立QA](stages/v5-key-safety/reviews/qa.md)。[范围](stages/v5-key-safety/reviews/scope.md) · [阶段](stages/v5-key-safety/stage.json)。

## 前阶段：已有用户名选择与密码手填

本机登录前可选已注册用户名，默认首项，密码自行填写；选择本身不登录，原认证/限频/归属保持。独立API 5项、一次V5构建及桌面浏览器主流程13项/模式切换窄补4项均通过；原始检查器失败保留。预览已生效，0模型/付费。本人已确认错误密码拒绝、跨账号关卡和存档进度隔离，原话及两张用户截图已归档，未外推整体安全。[交付/边界](stages/v5-login-usernames/reviews/delivery.md) · [独立QA](stages/v5-login-usernames/reviews/qa.md)。[阶段](stages/v5-login-usernames/stage.json) · [本人步骤](human-reviews/v5-login-usernames/round-01/review.md)。

## 前阶段：关卡生成可靠性改进

命名指导共用现有校验词表，原准入保持；独立窄验后，用户批准的6个真实受控样本均通过准入及EXIT规则回放，用量计费估算0.04783912元（非账单）。本地改进已生效，本人随后实际反馈“已经测试关卡生成成功率提升”，作为定性确认保存，未填写具体比例。[交付/边界](stages/v5-generation-reliability/reviews/delivery.md) · [计划](../../docs/v5-generation-reliability-plan.md) · [阶段](stages/v5-generation-reliability/stage.json) · [本人检查](human-reviews/v5-generation-reliability/round-01/review.md)。开发中旧预检不能当最终批准来源；正式approval及真实逐项结果保留，离线/真实/真人结论分开。

## 前阶段：取消人工生成累计次数上限

移除3/10分钟、10/日累计门，保留原在途/幂等/费用约束。8项独立窄验通过：[阶段](stages/v5-generation-attempts/stage.json) · [只读失败阶段诊断](stages/v5-generation-attempts/logs/latest-failures-summary.json) · [独立QA](stages/v5-generation-attempts/reviews/qa.md) · [本人步骤](human-reviews/v5-generation-attempts/round-01/review.md)。次数修复不代表narrative拒绝质量已修。

## 前阶段：生成入口选择已有主题

五个已有主题选择替代自由输入，保持原生成链与旧关卡。必要联合检查完成，待本人查看：[交付/局限](stages/v5-theme-selection/reviews/delivery.md) · [独立QA](stages/v5-theme-selection/reviews/qa.md) · [本轮记录](stages/v5-theme-selection/stage.json) · [本人检查](human-reviews/v5-theme-selection/round-01/review.md)。0真实/付费调用，不重跑旧全套。

## 前阶段：五类主题内部变化扩充

新31原图（15背景、8资料/钥匙、8设备状态）与稳定选图已接入，已完成一次V5构建和194条独立定向检查，待本人集中核验。固定入口：[交付/限制](stages/v5-theme-variation/reviews/delivery.md) · [独立QA](stages/v5-theme-variation/reviews/qa.md) · [阶段](stages/v5-theme-variation/stage.json) · [评价标准](stages/v5-theme-variation/evaluation/criteria.md) · [制作日志](stages/v5-theme-variation/logs/image-generation.json) · [本人待检查](human-reviews/v5-theme-variation/round-01/review.md) · [本地图集](../../美术图集.html)。累计74个独立图片来源；图集86卡片中的共享重复不另计。

## 前阶段：四类校园主题素材库

28张新原图已接入图书馆、化学实验室、机房和广播室；原天文社保留，通用物件共享。[本地双击图集](../../美术图集.html)（无需启动服务） · [网页图集](http://127.0.0.1:8001/art-themes/campus-theme-library.html) · [交付/限制](stages/v5-campus-theme-library/reviews/delivery.md) · [独立QA](stages/v5-campus-theme-library/reviews/qa.md) · [逐张制作记录](stages/v5-campus-theme-library/logs/image-generation.json) · [本人检查](human-reviews/v5-campus-theme-library/round-01/review.md)。一次构建与分范围联合检查完成，两次列表/就绪提示失败保留；本人尚未核验。

## 前阶段：门锁与门禁通行语义修正

用户已选择门锁/门禁负责通行，柜子仅负责真实线索和物品；画风/主题获得本次局部认可，整体仍待核验。新阶段见[实施计划](../../docs/v5-passage-semantics-plan.md)、[阶段记录](stages/v5-passage-semantics/stage.json)、[独立QA](stages/v5-passage-semantics/reviews/qa.md)和[本人检查入口](human-reviews/v5-passage-semantics/round-01/review.md)。已有定义和存档保留原名，新生成采用用途/命名规则。

## 前一阶段：手绘重建、UI修复与电脑端清理

2026-10-29追加HP-01名称点击修复：[真实反馈round-01](human-reviews/v5-handpainted-rebuild/round-01/review.md)、[独立检查](stages/v5-handpainted-rebuild/reviews/hotspot-pointer.md)、[随后本人反馈round-02](human-reviews/v5-handpainted-rebuild/round-02/review.md)。鼠标按下动效覆盖居中已修复，实际游戏定向联合通过；本次新反馈认可画风/主题并提出通行语义问题，没有明确确认HP-01。

- [本阶段交付摘要](stages/v5-handpainted-rebuild/reviews/delivery.md)：4项UI修复、15张实际手绘原图、经典/V5电脑端范围；技术联合检查通过，待本人检查。
- [手绘/UI独立QA](stages/v5-handpainted-rebuild/reviews/qa.md)、[电脑端构建](stages/v5-handpainted-rebuild/automated/desktop-cleanup-build1/result.json)、[最终桌面窄补](stages/v5-handpainted-rebuild/automated/desktop-smoke-2026-10-29T05-41-37-562Z-adadb34b/result.json)。各轮范围分开，原失败保留。
- [阶段状态](stages/v5-handpainted-rebuild/stage.json)与[本人检查步骤](human-reviews/v5-handpainted-rebuild/round-02/review.md)：round-01记录点击问题；round-02已收到画风/主题局部认可和通行语义修改要求，整体未登记接受。
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
