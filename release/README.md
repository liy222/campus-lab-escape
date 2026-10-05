# 交付索引

本项目是本机课程工程原型，当前文档按截至 2026-10-05 的已留存结果整理。T30 接受的产品候选是当前工作树原始源码身份（规则文件 SHA256 `73a77e8bbc9a26d59a9519315af99f8c640c5447e8e41cff303229278d850bbb`），关卡 2.0.0、接口/Schema/工具 1.0.0。此值不是新提交号；T30 未独立验证其 archive 中记录的历史 v1 commit。

## 源码、运行和回退

- `backend/app/`、`frontend/`：本地规则服务和网页。仓库根 README 给出指定 Python、Node 安装、mock 启动、保存恢复、服务停止以及 v2 独立数据库步骤。
- `scripts/`：本地开发和检查入口。`python -m scripts.dev --provider mock` 同时运行本地后端与前端；停止时按 Ctrl+C。
- `release/archives/baseline_v1/`：原 v1 回退源。README 使用 `./data/game-v1.sqlite` 与 v2 的 `./data/game-v2.sqlite` 分库，使用前关闭另一版本以释放默认端口。
- `docs/execution-plan.md` 保留完整要求；不是实现或验收记录。当前实际记录见 `docs/report.md`、`docs/defense.md` 和下列原始 QA 报告。

## 按要求编号查证

原始 R01–R18 与 A01–A28 定义在 `docs/execution-plan.md` 的第 3 节和第 18 节。以下是证据入口，不代表每项都通过；逐条结论以原报告的范围和选择器为准。

| 要求/验收范围 | 实际证据入口 | 当前可作的陈述 |
|---|---|---|
| R01–R13；A01–A23 中早期状态、接口、会话、建议和保存恢复项 | `review/findings/T08-report-20261002.md`、`review/findings/T13-report-20261002.md`、`review/findings/T18-report-20261002.md` 及各自所列 `evidence/qa/`；T30 追加 CH01 快照/重启覆盖见下行 | 只按各历史报告列出的版本和验收范围引用；不能从后续工程检查反推真人使用或整项目完成。 |
| R02、R04、R08、R16；A02、A12、A14、A21、A23、A27、A28 相关 CH01/v2 结果 | `review/findings/T30-report-20261005.md`；`evidence/qa/T30-evidence-index-20261005.json` 中 `T30-CH01-*`、`T30-RT02`–`T30-RT05`、`T30-V1-ROLLBACK` | 独立 T30 在固定 CH01 / RT01–05 范围 PASS；API 54 项、构建 exit 0、pytest 73 collected（含 19 个重用项）、203 子项；Chrome/Edge 六路由与三个视口通过。该报告不提供 RT06 结论。 |
| R14；A24 实验 | `review/findings/T23-independent-pilot-20261005.md`、`review/findings/T25-independent-formal-20261005.md`、`evidence/qa/T25-independent-20261005T055600Z/result.json` | Pilot 六次完成；正式比较停在 22 完成、1 超时、49 未调用。T25 对已停结果的 1829/1829 检查通过，完整三重复目标未达成，不作优劣结论。 |
| R15；A25 评价器及 RT06 结构读取 | `review/findings/T26-acceptance-20261003.md`、`review/findings/T27-evaluation-events-20261005.md`、`evidence/qa/T27-evaluation-events-20261005T105300Z/result.json` | T26 工程回归 193 项通过；T27 事件注册/固定归档独立检查 168/168 加必要旧回归 114/114。当前事件 RT06 结构结果仍为 `INSUFFICIENT_EVIDENCE`；真实付费校准未执行。 |
| R05–R11、R16；A07–A10、A15–A19、A27 中本次覆盖的注入边界、幂等、会话、恢复和 CH01 | T30 报告及 `T30-evidence-index-20261005.json` 对应 `T30-CH01-*` / `T30-RT01`–`T30-RT05` 选择器 | RT01 是脚本化 mock 结构边界检查；不证明真实模型语言层抗注入。CH01 失败及修正记录保留在报告中。 |
| R17；A28 干净交接 | `evidence/delivery/T32-preparation-20261005/report.md`、`checks.json` | 仅隔离 helper 准备检查完成；候选源码包的干净目录安装、pytest/build、服务恢复仍未运行。T30 v1 临时 DB 探针只证明对应窄回退行为。 |
| R18；A01/A18/A26 等签署、责任、证据索引相关要求 | `review/findings/T21-identity-review-20261002.md`、T25/T27/T30 报告、`docs/defense.md` | 保存了工程责任与证据身份记录；真人试玩、玩家实际决策和人类/教师签署未提供。不能声称完成这些人类活动。 |

上述表格提供已有记录的导航。没有在表格中列为 PASS 的验收项仍待对应 Owner 报告或实测补齐；不要用测试总数替代每项的原始判据。

## 实验与费用事实

- Pilot：六条真实 provider 结果由 T23 独立复核，3/3 完成每种上下文、各 2/3 正确；C06 两条已完成但下一步不正确。总计 ¥0.02975152 是保守账面计费，不是独立供应商账单。详见 T23 报告。
- 正式 E1：72 个计划格中实际记录为 22 完成、1 次超时、49 未调用；超时回复、送达和 token 仍未知。原 T25 检查的上界 ¥0.23749696 是当时未知状态下的保守上界。
- Main 后续根据用户报告的超时费用 ¥0.05 关闭账目时保留全部 ¥0.16292 上界并保留 token 为 NULL。当前累计上界 ¥0.27760296、35 笔已结算、无 pending/unknown；这不是供应商账单，也没有把 T25 历史观察改写成已知响应。
- 49 项 continuation 是独立新 run，保留原超时与错误输出、不重试 22 次完成记录；目前仍在进行，待 Main 获得并复核终态证据。不要把它和旧 49 条 not_called 混称为已完成。

## 尚未完成

- 49 项 continuation 的最终运行结果和独立复核。
- 评价器真实语义判读/付费校准；RT06 当前仍 `INSUFFICIENT_EVIDENCE`。
- T32 使用固定候选源码包在新目录安装、运行和保存恢复的完整干净复现。
- 用户亲自游玩和提供真实的人类决策/签署记录（如课程需要）。这些没有任何虚构替代。

未进行公开部署。没有启用 GitHub Actions。历史的 T30 自动化浏览器覆盖不是人类试玩。

本次文档整理记录见 `evidence/delivery/T31-docs-20261005/report.json`。
