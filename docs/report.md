# 当前工程与验收报告

更新日期：2026-10-06。本文汇总可核验事实，不将接受的计划或局部工程检查写成完整交付。

## 产品版本与本地数据隔离

产品版本为 `CH01_v2`，tag 已推送，commit `242ecfc4d9f7bf1a8480508de701d9efc7822fe7`。源码与证据身份见 [`evidence/integration/CH01_v2-manifest.json`](../evidence/integration/CH01_v2-manifest.json)：170 个源码、7 项证据，保留2个历史 harness 绑定缺口。v1回退基线commit为 `7821af4efe0613c20a80ea164c1dab1c0f288bab`，清单 `../evidence/integration/baseline_v1-manifest.json`。v1与v2使用不同数据库。

本地 v2 必须显式设置 `SQLITE_PATH=./data/game-v2.sqlite`，使用指定 Conda Python `C:\Users\liyh\.conda\envs\1\python.exe` 和 mock Provider。启动、停止、保存恢复及v1回退步骤见仓库 README。v1网页演示前需在归档目录运行 `npm.cmd --prefix frontend ci`，因为归档不含 `node_modules`。

较早 fc70 T32 包（6014文件）及其独立只读检查按历史路径保留。最新 clean 源码绑定至commit `833aafb09ad20dc1ba82cfed198485ce13300067`：10,778个文件逐字节匹配，Main执行8项外层检查和3项身份precheck，均exit 0；v1/v2服务重启恢复通过。证据为 [`Main clean report`](../evidence/integration/T32-clean-final-20261005T115741Z/report.json)、[`final source pins`](../evidence/integration/reproduction-20261005T115741Z-pins.json) 和 [`independent read/hash QA`](../evidence/qa/T32-final-20261005T123100Z/result.json)。独立检查10,842/10,842、exit 0，另有2项静态补充说明。该检查复用现有Windows/Conda环境，不代表新OS或新Python环境。

## 已有独立工程证据

T30独立CH01检查在冻结范围内PASS/STOP，无实现Finding。API runner 54个命名用例通过；构建exit 0，pytest收集73项和203子项，其中19项是复用方法；Chrome/Edge六个路由在三个视口完成本地自动化覆盖。范围限于mock/scripted Provider，不是人类试玩或真实模型语言安全证明。

旧T27事件注册和固定归档QA为新增168项及必要旧回归114项。CH01 v3身份/别名增量独立QA为79/79、exit 0，见 [`T27 CH01 event QA`](../review/findings/T27-CH01-event-20261005.md) 与其结果 [`result.json`](../evidence/qa/T27-CH01-event-20261005T115700Z/result.json)。该QA验证固定身份、归档绑定和合成协议；不代表语义验收或评价分数。

E1 pilot的六个真实调用经T23独立复核，每个上下文完成3条、正确2条。原正式E1历史run仍为22完成、1超时、49未调用；T25对该历史run的1829/1829检查通过。原超时的响应、送达和token仍未知。Main按用户报告费用保留FULL上界和NULL token；历史账面上界不是供应商发票或token还原。

## 实验、判读与费用

49项continuation离线执行器QA为449/449。真实有限运行选择49项，实际48次调用、47次返回、1次 `MODEL_UNAVAILABLE` 用量未知，另1项未调用；Main随后停止付费派发。原22完成和1超时没有重放。新run独立合并QA最终记录为 [`T25 merged result`](../evidence/qa/T25-merged-20261005T160549469322Z/result.json)，SHA256 `86fb081727330f055ef05af51110ce5ab37649ebd9cc9151e22afe41feb2f405`；1427/1427检查通过、exit 0、结论STOP。72计划格中69有终态、2 failed、1 not_called；有34个完整配对，独立离线重判69条旧记录。没有达成完整三重复，不能得出统计优胜结论。早期QA失败与后续修正证据均保留，最终结果只引用160549目录。

最新Main快照为101 settled calls、保守累计上界¥0.81685848、cap ¥10、pending 0、frozen 0；新8次调用已知用量合计¥0.1484352是调用元数据，不是供应商发票。用户报告的单次¥0.09已按Main规则保守登记；未知调用的FULL上界和NULL用量仍保留。该账本不是独立供应商账单。旧K1/K2结果10/11不变。随后6个获批新载荷各调用一次：K4模型输出有效，按预期判 `FAIL`；E1两条付费判读因无效reference/Schema问题均为 `INSUFFICIENT_EVIDENCE`；CH01三条因两条fake/unread references及一条1000字符无效输出，均为 `INSUFFICIENT_EVIDENCE`。报告分别见 [`E1 evaluation`](../evaluation/runs/20261005T155830386817Z/report.json)、[`CH01 evaluation`](../evaluation/runs/20261005T155947272680Z/report.json) 和 [`K4 result`](../evidence/integration/remaining-k4-20261005.json)。这六项不构成评价器通过或语义PASS。

## 评价器提示词修正

独立离线QA已对提示词修正版完成 SOURCE STOP：36个新场景、223项检查、30份捕获载荷、81个文件SHA前后不变，实际exit 0。报告见 [`T27 prompt-fix QA`](../review/findings/T27-prompt-fix-20261006.md)，结果与索引见 [`QA result`](../evidence/qa/T27-prompt-fix-20261005T163034187429Z/result.json) 和 [`QA index`](../evidence/qa/T27-prompt-fix-20261005T163034187429Z/index.json)。QA测试源码单独绑定至 `f80c6af075f6041aa11a4f79ba2e6cb1ea9ecd80`；Main离线接受记录为 `../evidence/integration/prompt-repair-accepted-20261006.json`，后续里程碑已推送并远端核验至 `c9f579209e702c957a560b1a2ad91f20fae6e8c8`。该离线检查不调用网络/模型，不证明真实判读效果。新提示2e977版的8项载荷已调用一次并经独立QA75/75 SOURCE STOP；校准11/11（3付费+8确定性对照），E1两项PASS仅针对冻结的登记Claim，72计划格仍为22完成/1超时/49未调用，CH01三项PASS仅针对当前冻结工程Claim。旧六项结果保持原样且不得重发：K4预期FAIL，E1两项及CH01三项INSUFFICIENT_EVIDENCE。
## R/A索引与剩余事项

R01–R18和A01–A28原文及课程映射见 `docs/execution-plan.md`。[`release/README.md`](../release/README.md)提供逐组证据入口；报告中的PASS只适用于所写版本、环境与检查范围。

提示词修正离线源码QA绑定 `f80c6af075f6041aa11a4f79ba2e6cb1ea9ecd80`，Main离线接受里程碑曾远端验证为`c9f579209e702c957a560b1a2ad91f20fae6e8c8`，与产品clean `833aafb`分开登记。之后2e977提示版8个有限载荷各调用一次并经75/75独立SOURCE STOP；仅对冻结Claim作出有限判读，不替代完整语义或真人验收。没有真人试玩、玩家实际决策、教师批准或人类签署；没有公开部署或GitHub Actions执行。

本次交付文档整理证据见 vidence/delivery/T31-docs-20261005/report-v5.json；report.json及report-v2/v3保留。

## A28 受限真实交互

A28 Main 实际执行 2 次 provider 调用、1 个 AI 轮次：inventory 工具读取后，返回已知线索并提议柜体码382，自动确认一次；确认重放未增加调用。独立 QA 105/105、exit 0、SOURCE STOP，核对 85 个只读文件未变、63 个固定源码匹配。证据：[`Main process`](../evidence/integration/A28-junction-real-process-20261006.json)、[`archive index`](../evidence/integration/A28-real-20261006/index.json)、[`QA report`](../review/findings/A28-real-result-20261006.md)、[`QA result`](../evidence/qa/A28-real-result-20261006T043600767538Z/result.json)。该结果是受限R1片段，不是完整自主通关或真人试玩。
