# 历史证据索引与迁移说明

旧证据可以迁移归档。当前采用保留来源的归档副本，将公开结果集中放入固定目录；被历史清单、代码或可信登记引用的原件先留兼容，内容不改写。后续清理旧路径时需同步处理引用，不能把归档日期当原执行日期。

## 本次已整理的入口

- [历史V5工程实验和有限评价](stages/history-v5-engineering/stage.json)：原E1/E2/E3结果、旧评价登记及离线判定自测，分别保持原来源范围。
- [当前E&O补齐](stages/2026-10-28-evaluation-observability/stage.json)：本轮11项API、两输入实际阶段、浏览器首轮和窄补、标准与复核。
- [修复前真人体验反馈](human-reviews/2026-10-28-generated-play-feedback/round-01/review.md)：用户原话及其明确提供的原截图；捕获时的确切源码版本未提供，不能反推为某次新版本验收。

## 原入口保持可读

| 材料 | 原位置 |
|---|---|
| 历史升级与V5验证 | [evidence/upgrade](../upgrade/) |
| 更早专项QA | [evidence/qa](../qa/) |
| 实验定义与说明 | [experiments/v5](../../experiments/v5/README.md) |
| 原工程评价器与历史运行 | [evaluation](../../evaluation/README.md) |
| 各阶段独立发现 | [review/findings](../../review/findings/) |
| 课程过程核查 | [原核查报告](../../output/reports/章节03_Evaluation与Observability_项目过程核查_20261028.md) |

不批量搬运私有模型原件、答案、witness、Cookie、Key或玩家数据库。这里的索引与阶段归档面向可读取、可提交的证据；历史私有材料继续按原排除规则保存。
