# V5当前交付总览（2026-10-30）

当前是本机开发候选。核心功能已实现并有分阶段技术结果；生成改善、账号隔离和Key界面已有对应真人反馈。五主题整体体验与课程语义评价等仍有未确认项，不能将整版记为发布验收通过。

本页汇总已有事实，不是一次新的源码全套测试。交付整理基线7bd8c40；最新产品改动d6806b1，生成命名改进66a54a6。各证据保留实际源码、执行时间、失败与范围，读取新汇总不会刷新旧评价登记。

## 先打开哪里

- 游戏：[http://127.0.0.1:8001/](http://127.0.0.1:8001/)。服务未启动时双击根目录[启动新版.cmd](../启动新版.cmd)。已有构建和依赖继续复用。
- 无需服务或Key的五主题图集：[美术图集.html](../美术图集.html)。游戏由后端执行，不能靠双击某个游戏HTML替代服务。
- 开发与交接：[HANDOFF-20261030.md](HANDOFF-20261030.md)；实际证据：[固定入口](../evidence/project/README.md)。

## 现在可以体验什么

| 能力 | 当前行为 | 已知边界 |
|---|---|---|
| 创建关卡 | 选择雨夜天文社、图书馆档案、化学实验室或计算机机房、校园广播室之一，再选1–3房间和难度 | 使用已有主题，不再手填；不是任意题材或任意新玩法 |
| 模型与程序协作 | 程序选合法骨架、编译、计算答案并证明/回放；模型填故事、名称与真实谜面参数；程序生成操作说明 | F/R有限结构及两资料族，36合同变体不是36种拓扑，允许重复 |
| 场景与美术 | 五主题累计74张当前主题原图；背景布局和物件外观有有限候选，场景与特写共源 | 不是74套关卡；新关卡稳定选图，刷新/读档不重选，旧关卡保留原外观 |
| 账号和存档 | 选本机已有用户名、自己填密码；私人关卡、进度、多时刻存档/读档/删除 | 登录前用户名可见；本机账号不是云账号，新旧版本数据库分开 |
| 提示与伙伴 | 免费三级规则提示；显式mock/真实伙伴入口复用现有系统 | 真实伙伴质量只在历史有限样本验证，未对五主题逐项实测 |
| 生成失败与密钥 | 人工创建取消累计次数门；保留在途/费用与幂等约束，不自动付费重试；Key临时使用和清空 | 用户1/global2在途、单次原费用上限保持；本机HTTP不代表公网部署方案 |

## 已实际确认的结果

| 范围 | 结果和来源 | 不可外推的部分 |
|---|---|---|
| 最近受控真实生成 | [本批摘要](../evidence/project/stages/v5-generation-reliability/evaluation/real-summary.json)：6/6准入、6/6领域EXIT回放；估算0.04783912元，非账单；[用户原话](../evidence/project/human-reviews/v5-generation-reliability/round-01/review.md)定性确认成功率提升 | 不是普遍成功率统计，不含新伙伴或评价；6次名额已用完 |
| 账号 | [独立专项](../evidence/project/stages/v5-login-usernames/reviews/qa.md)：API5项、一次构建、浏览器主流程13项和模式切换4项分开通过；[本人原话及两张原图](../evidence/project/human-reviews/v5-login-usernames/round-01/review.md)确认错密拒绝、关卡与存档进度隔离 | 不是全部鉴权场景或整站渗透结论 |
| Key界面 | [最终专项](../evidence/project/stages/v5-key-safety/reviews/qa.md)：10条记录、42个API响应扫描、未读0；提交/刷新/退出/跨页换号清空；[本人反馈](../evidence/project/human-reviews/v5-key-safety/round-01/review.md)“测试成功” | 自动测试用Synthetic，失败由本地模拟；本人未附图，辅助图明确标注自动来源 |
| 美术/界面 | [手绘交付](../evidence/project/stages/v5-handpainted-rebuild/reviews/delivery.md)、[点击修复](../evidence/project/stages/v5-handpainted-rebuild/reviews/hotspot-pointer.md)、[通行语义](../evidence/project/stages/v5-passage-semantics/reviews/delivery.md)、[四包](../evidence/project/stages/v5-campus-theme-library/reviews/delivery.md)、[变化扩充](../evidence/project/stages/v5-theme-variation/reviews/delivery.md)均有各自定向结果；画风/主题曾获[局部认可](../evidence/project/human-reviews/v5-handpainted-rebuild/round-02/review.md) | 不将旧要求修改记录静默关闭，不冒充五主题整体验收；历史失败和源码轮次保留 |

## 总计划26项要求：证据索引与实际范围

这里的“历史”指原候选已经执行的专项，不是当前整包重新通过。表格给出核查入口，不将资料存在等同于需求全部验收；需求定义以[正式计划](v5-build-plan.md)为准。

| Req | 可核查证据 | 当前结论/限制 |
|---|---|---|
| GEN-01 | [近期6真实样本](../evidence/project/stages/v5-generation-reliability/reviews/delivery.md) | 本批真实通过；主题/生成总体质量仅有限确认 |
| GEN-02 | [原准入与坏例](../review/findings/v5-offline-joint.md)、[结构专项](../review/findings/v5-structure-diversity.md) | 历史负例拒绝；原校验未放松，无当前全套新执行 |
| GEN-03 | [结构专项](../review/findings/v5-structure-diversity.md) | 36合同变体历史合成证明/回放；非36种拓扑 |
| GEN-04 | [原生成专项与必要补验](../review/findings/v5-offline-joint.md) | 原失败/未知/不重发覆盖；旧unknown仍未知 |
| USER-01 | [本人资源隔离](../evidence/project/human-reviews/v5-login-usernames/round-01/review.md)、[原私有ID专项](../review/findings/v5-offline-joint.md) | 本人确认关卡/进度隔离，原端点交换证据保留 |
| USER-02 | [原集成恢复](../review/findings/v5-offline-joint.md)、[结构兼容](../review/findings/v5-structure-diversity.md) | 原重登/进程重开覆盖，不计今天新重启测试 |
| USER-03 | [最新auth专项](../evidence/project/stages/v5-login-usernames/reviews/qa.md) | 错密、CSRF及原限频节点窄验；本人确认错密拒绝 |
| KEY-01 | [Key专项](../evidence/project/stages/v5-key-safety/reviews/qa.md) | 当前界面Synthetic允许传输/存储检查通过；非真实Key取证 |
| KEY-02 | [Key跨页专项](../evidence/project/stages/v5-key-safety/reviews/qa.md)、[原迟到/身份集成](../review/findings/v5-offline-joint.md) | 当前跨页清空与旧迟到保护分开，不拼成新全套 |
| COST-01 | [原生成/事务专项](../review/findings/v5-offline-joint.md) | 幂等/未知预留按原证据；不改账、未新付费 |
| COST-02 | [人工次数修订](../evidence/project/stages/v5-generation-attempts/reviews/delivery.md) | 取消累计次数限制，保留在途/原费用；8项受影响检查 |
| SAVE-01 | [原坏档保护](../review/findings/v5-offline-joint.md)、[定义兼容专项](../review/findings/v5-structure-diversity.md) | 原hash/版本拒绝及不覆盖；不是最新手工坏档试验 |
| SAVE-02 | [原三时刻/删除/reset](../review/findings/v5-offline-joint.md)、[本人存档隔离](../evidence/project/human-reviews/v5-login-usernames/round-01/review.md) | 原功能证据+本人隔离确认，整体流程仍可集中体验 |
| SYNC-01 | [原集成/重放](../review/findings/v5-offline-joint.md) | 旧rev/gen和冲突历史专项，未重复旧套件 |
| AI-01 | [原公开上下文专项](../review/findings/v5-offline-joint.md)、[历史真实A1/A2](../review/findings/v5-round3-real.md) | 原公开上下文与有限对话，不代表当前五主题真实伙伴质量 |
| AI-02 | [原安全与模拟伙伴专项](../review/findings/v5-offline-joint.md) | 有限注入/权限边界证据，非任意自然语言安全保证 |
| WEB-01 | [原恶意内容专项](../review/findings/v5-offline-joint.md) | 历史拒绝/文本显示边界；本轮未新增Web渗透 |
| WEB-02 | [原Host/CSRF/文件专项](../review/findings/v5-offline-joint.md)、[最新auth窄验](../evidence/project/stages/v5-login-usernames/reviews/qa.md) | 历史静态/来源保护与新auth节点分开，不称全站认证 |
| API-01 | [原合同专项](../review/findings/v5-offline-joint.md)、[新可选用户名字段检查](../evidence/project/stages/v5-login-usernames/reviews/qa.md) | 当前可选字段兼容/20路由已窄验，其他合同用原范围 |
| UI-01 | [桌面手绘/UI](../evidence/project/stages/v5-handpainted-rebuild/reviews/delivery.md)、[热点修复](../evidence/project/stages/v5-handpainted-rebuild/reviews/hotspot-pointer.md) | 当前仅1280×720/1920×1080鼠标键盘，按各轮结果保留 |
| ASSET-01 | [四主题包](../evidence/project/stages/v5-campus-theme-library/reviews/delivery.md)、[变化扩充](../evidence/project/stages/v5-theme-variation/reviews/delivery.md) | 当前74原图及有限候选接入；五主题整体本人接受仍待明确 |
| LEGACY-01 | [原旧版回归](../review/findings/v5-offline-joint.md)、[桌面清理交付](../evidence/project/stages/v5-handpainted-rebuild/reviews/delivery.md) | 旧库/入口保留，未重跑旧全套或迁移玩家库 |
| ENG-01 | [固定证据入口](../evidence/project/README.md)、[E&O标准](v5-evaluation.md) | 来源/执行/失败/反馈分开；旧登记保持原身份和范围 |
| ENG-02 | [E1/E2/E3原实际结果](../evidence/project/stages/history-v5-engineering/automated/experiments/result.json) | 历史9正常/20坏例等实验，不计本阶段新实验 |
| EVAL-01 | [有限评价状态说明](../evaluation/v5/README.md) | 离线适配/校准与确定性缺证分开；没有真实语义PASS |
| DELIVERY-01 | [最新接管包](HANDOFF-20261030.md)、[运行说明](../release/V5.md) | 启动与数据政策可读；本人全流程接管/回退和整体接受尚待实际反馈 |

## 剩余项与下一步

1. 请本人集中看五主题美术和当前完整游玩流程；账号及Key已经确认的部分不要求重测。已有图集和本人已有生成关卡可用，不必为验收再生成付费关卡。
2. 当前AI自然度、普遍成功率、真人难度/时长和五主题伙伴质量只保留有限证据，不自行扩大真实采样。
3. E1/E2/E3和评价离线材料可提交；旧C1/C2/C3评价仍非真实语义PASS，旧三条unknown门控保留。没有新的真实调用批准，不执行付费评价或更改旧账本/登记。
4. 本轮集中交接并正常提交推送。版本tag、合并main、部署、Actions、老师/同伴签字和整版接受未发生。

## 请本人集中检查一次

- 打开根目录美术图集，查看五主题背景/物件及变化是否符合预期；自动图是辅助，不冒充本人截图。
- 从本人已有生成关卡继续，检查物件标签易点、门锁/门禁控制通行、柜子提供资料/物品，场景与特写一致。
- 在已有关卡选一次存档继续、使用免费分级提示，核对体验是否达到本版本交付预期；不需要真实伙伴或新增生成。

反馈可以直接说“整体通过”或指出具体主题/步骤的问题；未附图时按已约定关联匹配的自动图，保留来源。该段是检查邀请，尚不是实际真人结论。
