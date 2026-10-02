# 交付索引

此索引按六类列出当前可核验材料。文件存在表示材料已保存；各条目注明对应的验收范围。M1/R1 已独立 QA 并推送，提交 `8a7348a09561102e5cb7146ad575349a2086bb30`。M2 手动范围已由独立 T13 API、浏览器及综合 checker 验收；当前工作树改动尚无对应提交 SHA。M2 验收不构成 baseline_v1 正式 manifest，也不替代 `STATUS.md`。

## 源码

- `backend/app/`：M2 手动游戏范围实现三房间规则及单槽保存/恢复/重置。
- `frontend/src/`：M2 手动三房间流程与保存/恢复/重置界面。
- `scripts/`：开发服务启动、检查与数据重置入口。
- `backend/requirements.lock.txt`、`frontend/package-lock.json`：依赖锁定文件。
- 限制：游戏 AI 与提案尚未开放；已验收的 M2 手动范围不代表项目整体完成。

## 契约

- `docs/SPEC.md`：冻结契约说明。
- `contracts/api.schema.json`、`contracts/tools.schema.json`、`contracts/tools.json`、`contracts/routes.json`：机器可读契约。
- `docs/level_design.md`：离线关卡设计资料。
- `contracts/validation.json`：契约验证材料。
- 限制：契约规定目标行为，不证明代码已经实现或满足所有条款。

## 检查

- `evidence/environment/delivery-build.txt`、`delivery-pip-check.txt`、`delivery-http-smoke.json`：交付环境与入口检查材料。
- `evidence/delivery/20261002-entry-review/report.json` 及同目录 `results.json`：检查入口审阅材料。
- `evidence/frontend/T07-report-20261002.md`：前端构建和 Owner 冒烟报告。
- `evidence/backend/m1_smoke_result_20261002.json`：后端冒烟结果。
- `evidence/qa/20261002T062147341889Z-r1-api/run.json`：T08 独立 API QA，记录 14 项、0 失败、1 项跳过，候选源码在运行期间未变化。
- `evidence/qa/20261002T062022883Z-r1-browser/run.json`：T08 独立浏览器 QA，记录 1280/768/390 视口运行，exit 0，候选源码在运行期间未变化；截图及检查明细在同目录。
- `evidence/qa/20261002T070100514544Z-m2-api/run.json`：T13 独立 API，27 tests、0 failures/errors/skips，exit 0，源码运行期间未变化。
- `evidence/qa/20261002T070144835Z-m2-browser/run.json`：T13 独立浏览器，1280/768/390 宽度完整三房间路线及存档/恢复/重置，exit 0，源码运行期间未变化。
- `evidence/qa/check/20261002T070319.030443Z-f6c70a6e/summary.json`：综合 checker PASS、exit 0、源码未变化；前端 build 0、pytest 27 passed 与 115 subtests；有 1 条 deprecation warning。
- 限制：这些 QA 只验收 M2 手动游戏和单槽控制；不覆盖游戏 AI、提案、实验、CH01、干净目录复现、真人试玩或整体发布验收。

## 证据

- `evidence/index-M0.json`：已接受 M0 基线证据索引。
- `evidence/delivery/docs-index-M2-accepted-20261002.json`：M2 手动范围证据摘要与验收界限。
- `evidence/backend/`、`evidence/frontend/`：候选实现冒烟与界面截图。
- `evidence/qa/20261002T062147341889Z-r1-api/` 和 `evidence/qa/20261002T062022883Z-r1-browser/`：T08 最终独立 QA 证据，分别覆盖 API 与浏览器视口流程；结果见上方“检查”。早期失败运行仍保存在各自时间戳目录中，作为修复前记录。
- `evidence/provider/handoff-20261002T064002444444Z/report.json`：独立 DeepSeek Provider adapter 工具请求及结果回传验证通过；累计 4 次真实请求，计费上限估算 ¥0.00230824，账单未核实。
- 限制：Provider adapter 验证不等于游戏 AI 已接入或可用；报告明确列出游戏 AI 集成、独立 QA、动态六工具授权、玩家轮次限制/确认及实验未验证。

## 变更

- `DECISIONS.md`：当前决定记录。
- `docs/task-dispatch.md`：任务分派和职责记录。
- `evidence/integration/recovery-20261002.json`：恢复过程记录。
- Git 当前提交和工作区状态由主负责人维护；本索引不记录未经核实的提交或发布版本。
- 未完成：没有 baseline_v1 正式 manifest；游戏 AI/提案、M3 相关实验与评价、CH01、干净目录复现及真人课程签署仍待完成，没有整体发布声明。

## 报告

- `STATUS.md`、`PLAN.md`：项目当前状态和计划。
- `review/M0-review.md`、`review/findings/QA-R1-001-scope-gap.md`：已有评审和 QA finding。
- `review/human-checkpoints.md`：人类检查点记录。
- `evidence/provider/handoff-20261002T064002444444Z/report.json`：真实 Provider adapter 验证报告；不证明游戏 AI 已接入或可供玩家使用，账单也未核实。
- 未完成：游戏 AI 集成与独立 QA、实验与评价、CH01、干净目录复现、真人课程签署。
