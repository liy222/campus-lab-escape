# 交付索引

此索引按六类列出当前可核验材料。文件存在表示材料已保存；各条目注明对应的验收范围。M1/R1 已独立 QA 并推送，提交 `8a7348a09561102e5cb7146ad575349a2086bb30`。M2 手动范围已由独立 T13 API、浏览器及综合 checker 验收并接受于 `165a961c9d6694ceb44c88ef86c1ea28de2eae71`。M3 已完成独立 mock QA 与一次受控真实游戏 AI 段，提交身份由 Main 在 STATUS 和冻结 manifest 中记录。M2 验收不构成 baseline_v1 正式 manifest，也不替代 `STATUS.md`。

## 源码

- `backend/app/`：M2 手动游戏范围实现三房间规则及单槽保存/恢复/重置。
- `frontend/src/`：M2 手动三房间流程与保存/恢复/重置界面。
- `scripts/`：开发服务启动、检查与数据重置入口。
- `backend/requirements.lock.txt`、`frontend/package-lock.json`：依赖锁定文件。
- `backend/app/ai/` 与前端 AI 面板：M3 可在 `--provider mock` 下问答并显示行动提案；提案参数由服务端固定，玩家确认后才执行，取消不执行。AI 单轮等待上限为 45 秒。
- 限制：mock 与真实段分开保存；受控真实段首次强制只读工具，不证明自然工具选择、完整 AI 通关或真人试玩。

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
- `evidence/ai/runs/20261002T113705132650Z/T14-T15-owner-report.json` 与 `evidence/backend/T16-owner-recovery-report-20261002.md`：Owner mock 检查和候选稳定交接报告；非独立验收。
- 限制：旧 T13 仅证明当时 M2；新增 M3 证据证明各自实际范围。实验、评价器、CH01、干净目录复现和真人试玩仍待完成。

## 证据

- `evidence/index-M0.json`：已接受 M0 基线证据索引。
- `evidence/delivery/docs-index-M2-accepted-20261002.json`：M2 手动范围证据摘要与验收界限。
- `evidence/backend/`、`evidence/frontend/`：候选实现冒烟与界面截图。
- `evidence/qa/20261002T062147341889Z-r1-api/` 和 `evidence/qa/20261002T062022883Z-r1-browser/`：T08 最终独立 QA 证据，分别覆盖 API 与浏览器视口流程；结果见上方“检查”。早期失败运行仍保存在各自时间戳目录中，作为修复前记录。
- `evidence/provider/handoff-20261002T064002444444Z/report.json`：独立 DeepSeek Provider adapter 工具请求及结果回传验证通过；累计 4 次真实请求，计费上限估算 ¥0.00230824，账单未核实。
- `evidence/ai/runs/20261002T113705132650Z/`、`evidence/ai/runs/20261002T113715376935Z/`：AI Owner mock 运行证据；无付费或真实网络调用。
- 限制：Provider adapter 与游戏段分别记录；游戏真实段为 1 轮受控联调，不能扩大成完整 AI 玩法或真人接受建议。

## 变更

- `DECISIONS.md`：当前决定记录。
- `docs/task-dispatch.md`：任务分派和职责记录。
- `evidence/integration/recovery-20261002.json`：恢复过程记录。
- Git 当前提交和工作区状态由主负责人维护；本索引不记录未经核实的提交或发布版本。
- 未完成：baseline_v1 manifest 正由 Main 冻结；实验与评价、CH01、干净目录复现及真人签署待完成，没有整体完成声明。

## 报告

- `STATUS.md`、`PLAN.md`：项目当前状态和计划。
- `review/M0-review.md`、`review/findings/QA-R1-001-scope-gap.md`：已有评审和 QA finding。
- `review/human-checkpoints.md`：人类检查点记录。
- `evidence/provider/handoff-20261002T064002444444Z/report.json`：Provider adapter 验证报告；不证明游戏 AI 真实模型验收通过，账单也未核实。
- 未完成：实验与评价、CH01、干净目录复现、真人签署。

## M3 当前实际结果

- `evidence/qa/20261002T120504699455Z-m3-api/run.json`：46 tests、0失败/错误/跳过，exit0。
- `evidence/qa/check/20261002T120553.430164Z-b81339d5/summary.json`：build0、pytest46 passed/159subtests、source_unchanged=true、exit0；1条现有deprecation提示。
- `evidence/qa/20261002T115503579Z-m3-browser/run.json`：Chrome与Edge各1280/768/390，AI加载、引用键盘定位、取消/确认、旧版本响应与确认结果不确定恢复，exit0。
- `evidence/qa/20261002T115601621Z-m2-browser/run.json`：当前手动三宽度全程通关、存档控制回归，exit0。
- `evidence/qa/20261002T120735404563Z-m3-real/run.json`：真实DeepSeek1turn/2calls，首次forced get_inventory→真实工具结果→开柜提案→测试玩家fixed{}confirm；重放无新call，exit0。本段保守上界0.00804624元；全项目累计0.01035448元，非账单核验。
- 原始QA脚本的Windows资源清理、随机ID误报、极短墙钟调度断言与旧响应按钮预期失败均保留于各时间戳目录；实际产品源码未因此改变。
- 版本绑定采用原始raw SHA256与Git blob/commit/tree及Main批准的CRLF→LF转换链；正式manifest生成后作为实验基线。真人试玩、接受/拒绝AI建议与签署均未提供。
