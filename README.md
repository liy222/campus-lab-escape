# 逃离校园实验室

这是一个本地运行的三房间网页解谜游戏：规则由后端执行，AI队友提供受限建议，推进游戏的建议需要玩家确认。当前工作版本为 v2（关卡 2.0.0；接口、Schema 与工具契约 1.0.0），已提交并推送为 `CH01_v2`（`242ecfc4d9f7bf1a8480508de701d9efc7822fe7`）。版本源码与证据绑定见 [`evidence/integration/CH01_v2-manifest.json`](evidence/integration/CH01_v2-manifest.json)。T30独立检查通过指定CH01/RT01–05工程范围。新源码目录复现绑定至833aafb（10,778文件，Main执行与10842项独立只读检查通过），详见[`交付总manifest`](release/manifest.json)；复用现有Windows/Conda，不代表新OS/新Python、真人试玩或人类签署。

## 本地启动 v2

在 Windows PowerShell 中，从仓库根目录执行。使用指定 Conda Python，不创建或重置环境：

```powershell
Set-Location -LiteralPath 'D:\深度能力'
$ProjectPython = 'C:\Users\liyh\.conda\envs\1\python.exe'
& $ProjectPython -m pip install -r backend/requirements.lock.txt
npm.cmd --prefix frontend ci
$env:SQLITE_PATH = './data/game-v2.sqlite'
& $ProjectPython -m scripts.dev --provider mock
```

真实 provider 接入可通过 `--provider deepseek` 选择；本地示例仍用 mock，密钥按项目配置在运行环境中提供，切勿写入文档。首次安装依赖后，日常启动可从设定 `SQLITE_PATH` 的命令开始。该路径明确为 v2 新库；不要把 v1 路径填入此变量。服务启动后打开 <http://127.0.0.1:5173/>。开发启动器会同时启动前后端并检查本地健康页。按 Ctrl+C 停止两项服务。

如需在本 PowerShell 窗口中清除变量，停止服务后执行：

```powershell
Remove-Item Env:SQLITE_PATH -ErrorAction SilentlyContinue
```

游戏界面的“保存”和“恢复”用于当前会话的单槽进度。服务重启后可用恢复操作继续；T30 已验证该行为及 v2 与归档 v1 快照的版本隔离。数据库属于本地运行数据，不是发布材料。

## 独立运行 v1 回退基线

v1 归档位于 `release/archives/baseline_v1/`。若要启动归档版本，应在新的 PowerShell 窗口使用其自身代码目录、独立数据库和 mock Provider：

```powershell
Set-Location -LiteralPath 'D:\深度能力\release\archives\baseline_v1'
$ProjectPython = 'C:\Users\liyh\.conda\envs\1\python.exe'
& $ProjectPython -m pip install -r backend/requirements.lock.txt
npm.cmd --prefix frontend ci
$env:SQLITE_PATH = './data/game-v1.sqlite'
& $ProjectPython -m scripts.dev --provider mock
```

归档副本没有前端 `node_modules`，首次网页演示前必须执行上面的 `npm.cmd --prefix frontend ci`；仅启动后端 API 时不需要前端依赖。归档版本也占用本机默认端口 8000/5173；启动前应先停止另一个版本。按 Ctrl+C 停止，关闭窗口后该窗口的环境变量也随之结束。v1 与 v2 的数据库文件名不同，必须保持隔离。T30 曾用临时数据库探测归档 v1；T32 又在新源码目录中实际启动归档 v1，独立 DB 完成 13 步、保存及 OS 服务重启恢复，并保留钥匙。完整复现范围与结果见 T32 报告；该范围仍使用现有 Windows/Conda 环境。

## 文档与证据

- 详细范围和 R01–R18、A01–A28 原始要求：[`docs/execution-plan.md`](docs/execution-plan.md)。它定义验收，不证明执行。
- 当前阶段报告：[`docs/report.md`](docs/report.md)。
- 个人答辩素材：[`docs/defense.md`](docs/defense.md)。
- T30 的独立 CH01 报告与逐项证据选择器：[`review/findings/T30-report-20261005.md`](review/findings/T30-report-20261005.md)、[`evidence/qa/T30-evidence-index-20261005.json`](evidence/qa/T30-evidence-index-20261005.json)。
- T27 评价器结构与事件检查：[`review/findings/T27-evaluation-events-20261005.md`](review/findings/T27-evaluation-events-20261005.md)。提示词修正版离线QA：[`review/findings/T27-prompt-fix-20261006.md`](review/findings/T27-prompt-fix-20261006.md)，223检查、36场景、30载荷、81文件不变；其后2e977版本8项实际判读另经 [`T27 revised result QA`](review/findings/T27-revised-real-result-20261006.md) 独立75/75 SOURCE STOP。A28另有受限真实R1片段和105/105独立QA，见 [`A28结果`](review/findings/A28-real-result-20261006.md)。
- 交付文档本次整理记录：[`evidence/delivery/T31-docs-20261005/report-v5.json`](evidence/delivery/T31-docs-20261005/report-v5.json)（前次修订在 `report-v2.json`，原始记录在 `report.json`，均保留）。

截至 2026-10-06 的证据仍有明确边界。产品版本为 `CH01_v2`（commit `242ecfc4d9f7bf1a8480508de701d9efc7822fe7`），v1回退commit `7821af4efe0613c20a80ea164c1dab1c0f288bab`，两者有独立源清单和本地数据库。Main 对 commit `833aafb09ad20dc1ba82cfed198485ce13300067` 的新源码目录复现 exit 0，10,778 文件逐字节匹配，8项外层检查及3项评价器precheck均通过；独立只读复核 10,842/10,842、exit 0，另有2项静态补充说明。范围仍是现有 Windows/Conda，不是新OS/新Python环境。E1 continuation 命令 exit 0，49计划项中48调用、47返回、1项 `MODEL_UNAVAILABLE` 用量未知、1项未调用；原22完成和1超时没有重放。新数据独立合并复核最终路径 `evidence/qa/T25-merged-20261005T160549469322Z/result.json` 为1427/1427、exit 0、STOP：69/72有终态、34个完整配对，另外2 failed、1 not_called；结论不支持完整三重复或统计优胜。最新Main快照为101 settled calls、保守上界¥0.81685848、cap ¥10、pending 0、frozen 0；新8次评价器调用的已知用量¥0.1484352为调用元数据，不是供应商发票。原K1/K2记录维持10/11。之后旧6项批准载荷各调用一次：K4模型有效且按预期判FAIL；E1两条与CH01三条为 `INSUFFICIENT_EVIDENCE`，保留原结论且不可重发。提示版本2e977的8项新载荷（校准3、E1 2、CH01 3）各调用一次，独立 QA 75/75 SOURCE STOP。校准11/11由3条付费判读与8项确定性对照构成；E1原登记批次判读2条PASS，但对应的72计划状态仍为22 completed、1 timeout、49 not_called，不能写成72完成；CH01三条PASS限于当前冻结工程Claim。CH01 v3身份/别名检查79/79通过，但不等于真实语义验收。没有真人试玩、玩家决策或人类/教师签署；没有公开部署。