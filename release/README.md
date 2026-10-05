# 交付索引

本项目是本机课程工程原型，交付资料按截至 2026-10-06 的已留存结果整理。机器可读总索引见 [`release/manifest.json`](manifest.json)。

## 源码、运行和回退

- `backend/app/`、`frontend/`：本地规则服务和网页。仓库根 README 给出指定 Python、Node 安装、mock 启动、保存恢复、服务停止以及 v2 独立数据库步骤。
- `scripts/`：本地开发和检查入口。`python -m scripts.dev --provider mock` 同时运行本地后端与前端；停止时按 Ctrl+C。
- `release/archives/baseline_v1/`：原 v1 回退源。使用 v1 的 `./data/game-v1.sqlite`，与 v2 的 `./data/game-v2.sqlite` 分库。归档没有 `node_modules`；网页演示前先在归档 cwd 执行 `npm.cmd --prefix frontend ci`，只运行后端 API 时无需安装前端依赖。使用前关闭另一版本以释放默认端口。
- `docs/execution-plan.md` 保留完整要求；不是实现或验收记录。当前实际记录见 `docs/report.md`、`docs/defense.md` 和下列原始 QA 报告。

## 按要求编号查证

原始 R01–R18 与 A01–A28 定义在 `docs/execution-plan.md` 的第 3 节和第 18 节。以下是证据入口，不代表每项都通过；逐条结论以原报告的范围和选择器为准。

| 要求/验收范围 | 实际证据入口 | 当前可作的陈述 |
|---|---|---|
| R01–R13；A01–A23 中早期状态、接口、会话、建议和保存恢复项 | `review/findings/T08-report-20261002.md`、`review/findings/T13-report-20261002.md`、`review/findings/T18-report-20261002.md` 及各自所列 `evidence/qa/`；T30 追加 CH01 快照/重启覆盖见下行 | 只按各历史报告列出的版本和验收范围引用；不能从后续工程检查反推真人使用或整项目完成。 |
| R02、R04、R08、R16；A02、A12、A14、A21、A23、A27、A28 相关 CH01/v2 结果 | `review/findings/T30-report-20261005.md`；`evidence/qa/T30-evidence-index-20261005.json` 中 `T30-CH01-*`、`T30-RT02`–`T30-RT05`、`T30-V1-ROLLBACK` | 独立 T30 在固定 CH01 / RT01–05 范围 PASS；API 54 项、构建 exit 0、pytest 73 collected（含 19 个重用项）、203 子项；Chrome/Edge 六路由与三个视口通过。该报告不提供 RT06 结论。 |
| R14；A24 实验 | `review/findings/T23-independent-pilot-20261005.md`、`review/findings/T25-independent-formal-20261005.md`、`review/findings/T25-merged-20261005.md`、`evidence/qa/T25-merged-20261005T160549469322Z/result.json` | Pilot六次；原正式run为22完成/1超时/49未调用；continuation合并独立复核1427/1427、exit0、STOP，69/72终态，完整三重复未达成，不作优劣结论。
| R15；A25 评价器及 RT06 结构读取 | `review/findings/T26-acceptance-20261003.md`、`review/findings/T27-evaluation-events-20261005.md`、`review/findings/T27-CH01-event-20261005.md`、`review/findings/T27-prompt-fix-20261006.md`、`evidence/qa/T27-prompt-fix-20261005T163034187429Z/result.json` | 旧固定源码检查168/168+114/114；CH01 v3身份别名79/79；提示词修正版离线独立SOURCE STOP为36场景/223检查/30捕获/81文件unchanged，exit0。此修正无真实模型调用。旧6次付费结果保持：K4有效模型预期FAIL，E1两条及CH01三条INSUFFICIENT_EVIDENCE；8个新载荷待批准。
| R05–R11、R16；A07–A10、A15–A19、A27 中本次覆盖的注入边界、幂等、会话、恢复和 CH01 | T30 报告及 `T30-evidence-index-20261005.json` 对应 `T30-CH01-*` / `T30-RT01`–`T30-RT05` 选择器 | RT01 是脚本化 mock 结构边界检查；不证明真实模型语言层抗注入。CH01 失败及修正记录保留在报告中。 |
| R17；A28 新源码目录交接 | `evidence/integration/T32-clean-final-20261005T115741Z/report.json`、`evidence/qa/T32-final-20261005T123100Z/result.json`、`evidence/integration/reproduction-20261005T115741Z-pins.json` | 新源码commit833aafb，10,778个文件按raw pins核对；Main执行8项外层检查和3项precheck均exit0。独立只读复核10,842/10,842、exit0，另有2项静态补充说明。现有Windows/Conda，不代表新OS/新Python或真人验收。较早fc70包和其独立复核另在T32历史目录，身份分列于manifest。
| R18；A01/A18/A26 等签署、责任、证据索引相关要求 | `review/findings/T21-identity-review-20261002.md`、T25/T27/T30 报告、`docs/defense.md` | 保存了工程责任与证据身份记录；真人试玩、玩家实际决策和人类/教师签署未提供。不能声称完成这些人类活动。 |

上述表格提供已有记录的导航。没有在表格中列为 PASS 的验收项仍待对应 Owner 报告或实测补齐；不要用测试总数替代每项的原始判据。

## 实验与费用事实

- Pilot：六条真实 provider 结果由 T23 独立复核，3/3 完成每种上下文、各 2/3 正确；C06 两条已完成但下一步不正确。总计 ¥0.02975152 是保守账面计费，不是独立供应商账单。详见 T23 报告。
- 正式 E1：72 个计划格中实际记录为 22 完成、1 次超时、49 未调用；超时回复、送达和 token 仍未知。原 T25 检查的上界 ¥0.23749696 是当时未知状态下的保守上界。
- Main根据用户提供费用信息保留原超时FULL上界与NULL token。最新91 calls、保守累计上界¥0.66236008、pending 0；该数字不是供应商账单。
- 49项continuation是独立run，离线执行器QA为449/449。实际48调用、47返回、1项MODEL_UNAVAILABLE且usage未知、1项未调用；最终独立合并QA为1427/1427、exit0、STOP（69/72终态，34个完整配对，2 failed/1 not_called）。完整三重复未达成，不作组间胜负结论。用户报告的¥0.09单次费用已保守登记，未知FULL上界保留。原22完成/1超时记录没有重放。

## 当前未完成范围

- 新提示修正的离线身份与边界复核已SOURCE STOP（36场景/223检查/30捕获/81文件unchanged），测试源码绑定`f80c6af`，Main离线接受里程碑为远端验证提交`c9f579209e702c957a560b1a2ad91f20fae6e8c8`。没有运行真实新版本判读；8个新载荷待用户批准。旧六次判读已各调用一次，不重发。
- 人类试玩、玩家决策、教师/人类签署仍未提供；不宣称课程或人类验收完成。
- 所有语义判读均无有效PASS；CH01 v3结构身份QA通过不替代语义验收。
- CH01 v3身份/别名独立QA为79/79；这只验证固定身份和合成协议，不是语义评价。

未进行公开部署。没有启用 GitHub Actions。历史的 T30 自动化浏览器覆盖不是人类试玩。

本次文档整理记录见 `evidence/delivery/T31-docs-20261005/report-v5.json`；v1–v3 历史记录保持原样。
