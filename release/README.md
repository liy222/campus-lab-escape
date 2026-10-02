# 交付索引

此索引按六类列出当前可核验材料。文件存在表示材料已保存，不表示其涵盖范围已验收通过。当前正式记录仍是 M0；M1/R1 的候选实现和 QA 正在核验。这里不构成 R1 release manifest，也不替代 `STATUS.md`。

## 源码

- `backend/app/`：后端候选实现；包含 `domain/`、`api/`、`storage/`。
- `frontend/src/`：R1 候选网页界面。
- `scripts/`：开发服务启动、检查与数据重置入口。
- `backend/requirements.lock.txt`、`frontend/package-lock.json`：依赖锁定文件。
- 未完成：M1/R1 尚未独立验收和冻结；AI、存档恢复及网页重置流程未开放。

## 契约

- `docs/SPEC.md`：冻结契约说明。
- `contracts/api.schema.json`、`contracts/tools.schema.json`、`contracts/tools.json`、`contracts/routes.json`：机器可读契约。
- `docs/level_design.md`：离线关卡设计资料。
- `contracts/validation.json`：契约验证材料。
- 限制：契约规定目标行为，不证明代码已经实现或满足所有条款。

## 检查

- `evidence/environment/delivery-build.txt`、`delivery-pip-check.txt`、`delivery-http-smoke.json`：交付环境与入口检查材料。
- `evidence/delivery/20261002-entry-review/report.json` 及同目录 `results.json`：检查入口审阅材料。
- `evidence/frontend/T07-build-20261002.log`、`evidence/frontend/T07-report-20261002.md`：前端构建和 Owner 冒烟报告。
- `evidence/backend/m1_smoke_result_20261002.json`：后端冒烟结果。
- 限制：这些是各自范围的检查，不能代替独立浏览器 QA、完整游戏通关或发布验收。

## 证据

- `evidence/index-M0.json`：已接受 M0 基线证据索引。
- `evidence/backend/`、`evidence/frontend/`：候选实现冒烟与界面截图。
- `evidence/qa/20261002T060937281797Z-r1-api/`：较早 API QA 运行记录；`run.json` 记录一次失败。
- `evidence/qa/20261002T061121871709Z-r1-api/`：后续 API QA 运行记录；`run.json` 记录 14 项、0 失败、1 项跳过，另有 `stderr.txt`。
- `evidence/qa/20261002T061508883Z-r1-browser/`：浏览器 QA 运行记录；`run.json` 有 R1 场景缺失失败。
- `evidence/qa/20261002T061724984Z-r1-browser/`：后续浏览器 QA 运行记录与视口截图。`checks.json` 保存检查细节；该次材料仍须由 QA 明确判定，当前不能标为通过。
- 限制：浏览器验收仍在执行中；候选证据不可替代正式签署或发布基线。

## 变更

- `DECISIONS.md`：当前决定记录。
- `docs/task-dispatch.md`：任务分派和职责记录。
- `evidence/integration/recovery-20261002.json`：恢复过程记录。
- Git 当前提交和工作区状态由主负责人维护；本索引不记录未经核实的提交或发布版本。
- 未完成：没有 baseline_v1 正式 manifest；M2/M3 未完成，也没有相应验收声明。

## 报告

- `STATUS.md`、`PLAN.md`：项目当前状态和计划。
- `review/M0-review.md`、`review/findings/QA-R1-001-scope-gap.md`：已有评审和 QA finding。
- `review/human-checkpoints.md`：人类检查点记录。
- `evidence/provider/probe-20261001T130457931379Z/report.json`：已有 Provider 探针报告；不构成当前网页真实 AI 可用或已验收的证据。
- 未完成：真实 DeepSeek 接入及调用验证、实验与评价、CH01、干净目录复现、真人课程签署。
