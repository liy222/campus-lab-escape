# 逃离校园实验室

这是一个本地运行的三房间网页解谜游戏：规则由后端执行，AI队友提供受限建议，推进游戏的建议需要玩家确认。当前工作版本为 v2（关卡 2.0.0；接口、Schema 与工具契约 1.0.0）。独立 T30 检查通过了指定 CH01/RT01–05 工程范围；项目尚未完成整套干净目录复现、真人试玩或人类签署。

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

首次安装依赖后，日常启动可从设定 `SQLITE_PATH` 的命令开始。该路径明确为 v2 新库；不要把 v1 路径填入此变量。服务启动后打开 <http://127.0.0.1:5173/>。开发启动器会同时启动前后端并检查本地健康页。按 Ctrl+C 停止两项服务。

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
$env:SQLITE_PATH = './data/game-v1.sqlite'
& $ProjectPython -m scripts.dev --provider mock
```

归档版本也占用本机默认端口 8000/5173；启动前应先停止另一个版本。按 Ctrl+C 停止，关闭窗口后该窗口的环境变量也随之结束。v1 与 v2 的数据库文件名不同，必须保持隔离。T30 已用临时 v1 数据库执行归档代码回退探针，exit 0；这不是一次新的用户目录恢复演练。完整安装与干净目录复现仍待 T32。

## 文档与证据

- 详细范围和 R01–R18、A01–A28 原始要求：[`docs/execution-plan.md`](docs/execution-plan.md)。它定义验收，不证明执行。
- 当前阶段报告：[`docs/report.md`](docs/report.md)。
- 个人答辩素材：[`docs/defense.md`](docs/defense.md)。
- T30 的独立 CH01 报告与逐项证据选择器：[`review/findings/T30-report-20261005.md`](review/findings/T30-report-20261005.md)、[`evidence/qa/T30-evidence-index-20261005.json`](evidence/qa/T30-evidence-index-20261005.json)。
- T27 评价器结构与事件检查：[`review/findings/T27-evaluation-events-20261005.md`](review/findings/T27-evaluation-events-20261005.md)。
- 交付文档本次整理记录：[`evidence/delivery/T31-docs-20261005/report.json`](evidence/delivery/T31-docs-20261005/report.json)。

所有证据只支持其报告标明的执行范围。实验停在 22 完成、1 超时、49 未调用；49 项 continuation 仍在进行且结果待 Main 复核。真实评价器付费校准、干净目录安装和完整交接仍未完成。真人试玩、玩家实际接受/拒绝建议的记录、教师签署或人类签署没有提供。没有公开部署。
