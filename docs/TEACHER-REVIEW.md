# 课程评阅与评分材料索引

本项目为《逃离校园实验室》。开发者为用户本人，AI参与实现、检查及材料整理；没有虚构其他组员、同伴验收或教师评分。当前代码在 `main`，最新功能实现 `cd0c238` 为共享与排行榜，11月5日本人检查于 `eea8e97` 归档。本索引只组织已有材料，不代表新的测试或评分。

## 建议阅读顺序

先看[项目首页](../README.md)和[当前状态](../STATUS.md)，再按下表阅读。对应课程的“意图 → 问题定义 → Specification → Plan/Tasks → Harness → 实现与证据”，每一环均提供可查看的版本化材料。

| 课程要求/表单项 | 仓库材料 | 可以核查什么 |
|---|---|---|
| 需求、问题定义 | [正式构建计划](v5-build-plan.md)、[共享扩展计划](v5-sharing-leaderboard-plan.md) | 需求来源、为什么做、用户流程、范围与不做项；计划不等于执行证明 |
| 可验证规约 | [基础SPEC](SPEC.md)、[正式计划验收矩阵](v5-build-plan.md)、[API合同](../contracts/v2/README.md)、[路由](../contracts/v2/routes.json)、[Schema](../contracts/v2/api.schema.json) | 稳定需求、规则、状态与失败条件，接口类型和隐私边界 |
| ADR、前置研究与取舍 | [DECISIONS](../DECISIONS.md)、[正式计划ADR与修订](v5-build-plan.md)、[结构设计专项](../review/findings/v5-structure-diversity.md) | 为什么采用程序合法骨架、AI内容变化、规则操作说明；代价与有限多样性 |
| 项目级Harness | [AGENTS](../AGENTS.md)、[观测与评价约定](v5-evaluation.md)、[检查入口](../scripts/check_v5.py)、[证据工具](../scripts/evidence_hub.py) | 文件归属、工具与权限、定向验证、日志/证据来源及付费约束；双层Harness设计见正式计划 |
| Global / Plan / Tasks | [PLAN](../PLAN.md)、[STATUS](../STATUS.md)、[正式计划任务卡](v5-build-plan.md)、[共享分阶段依赖](v5-sharing-leaderboard-plan.md) | 总目标、依赖、文件归属、验收条件、实际完成及剩余范围 |
| 可执行代码与评测证据 | [后端](../backend/app/)、[前端](../frontend/src/v5/)、[测试](../tests/v5/)、[固定证据入口](../evidence/project/README.md)、[全部阶段索引](../evidence/project/index.json) | 代码、实际测试入口、运行结果/退出码、截图、失败与修复、真人反馈 |
| 其他：数据/训练说明 | [V5工程实验](../experiments/v5/README.md)、[评价器](../evaluation/v5/README.md)、[历史实验目录](../experiments/) | 使用有限合成数据与真实样本；本项目没有声称训练或微调模型，无需虚构训练材料 |

## 优先核查的实际证据

| 主题 | 自动执行/评价 | 本人核验及范围 |
|---|---|---|
| 最新共享与排行榜 | [交付](../evidence/project/stages/v5-sharing-leaderboard/reviews/delivery.md)、[独立QA](../evidence/project/stages/v5-sharing-leaderboard/reviews/qa.md)、[阶段元数据](../evidence/project/stages/v5-sharing-leaderboard/stage.json) | [11月5日原话、9张不同原图及10附件来源](../evidence/project/human-reviews/v5-sharing-leaderboard/round-01/review.md)：同轮读档继续计时、跨轮练习、排行及取消后的访问等；未自动扩为整版接受 |
| 账号与私有数据隔离 | [API及桌面检查](../evidence/project/stages/v5-login-usernames/reviews/qa.md) | [错误密码拒绝、跨账号关卡/存档隔离及本人截图](../evidence/project/human-reviews/v5-login-usernames/round-01/review.md) |
| Key临时使用及清空 | [专项实际结果](../evidence/project/stages/v5-key-safety/reviews/qa.md) | [本人反馈及自动辅助图来源](../evidence/project/human-reviews/v5-key-safety/round-01/review.md)，自动图不冒充本人截图 |
| 生成可靠性 | [六次获批真实样本](../evidence/project/stages/v5-generation-reliability/evaluation/real-summary.json)、[交付边界](../evidence/project/stages/v5-generation-reliability/reviews/delivery.md) | [本人定性反馈](../evidence/project/human-reviews/v5-generation-reliability/round-01/review.md)；六次成功不外推总体成功率 |
| 美术/主题与UI | [手绘重建](../evidence/project/stages/v5-handpainted-rebuild/reviews/delivery.md)、[五主题变化扩充](../evidence/project/stages/v5-theme-variation/reviews/delivery.md)、[无需服务的图集](../美术图集.html) | [画风局部反馈](../evidence/project/human-reviews/v5-handpainted-rebuild/round-02/review.md)，五主题整体接受尚未明确 |
| Evaluation与Observability | [标准/观测设计](v5-evaluation.md)、[工程实验原结果](../evidence/project/stages/history-v5-engineering/automated/experiments/result.json)、[有限C1–C3实际真实评价](../evidence/project/stages/v5-conservative-recovery/reviews/execution.md) | [本人接管原话](../evidence/project/human-reviews/v5-current-evaluation/round-01/review.md)；真实评价为11月2日固定源码范围，不覆盖后续共享实现 |

## 如何理解证据

- `evidence/project/stages/` 是分阶段结果入口，`human-reviews/` 单独存本人原话及来源。旧 `evidence/upgrade/`、`evidence/qa/`、`experiments/`、`evaluation/` 和 `review/` 原件继续保留在Git，固定登记/pin没有移动或改写。
- 同一阶段可能先失败再窄补成功；原退出码、运行时间与源码范围保留，不能拼成一次新全套通过。自动截图、用户截图、合成夹具及真实模型样本分别标注。
- 11月2日三个有限Claim的真实PASS不是整站安全认证或共享代码的新评价；本次仓库整理没有运行产品测试、构建、浏览器或付费模型。
- 精简前的首页、完整计划及状态正文在[原文归档](history/repository-notes-20261111/README.md)，源提交及逐字节校验信息可查；[DECISIONS](../DECISIONS.md)及所有阶段证据未删除。Git本身保留完整81个开发提交。
- 当前仍无整版发布tag、公网部署、真实同伴/教师签字或评分。需要对抗组实验时，已有工程实验和负例可作为材料；两组实际合作过程尚不能预填完成。
