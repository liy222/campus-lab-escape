# 逃离校园实验室

这是一个本地运行的三房间网页解谜游戏：规则由后端执行，AI队友提供受限帮助；旧版本中的推进建议须由玩家确认。本地 v3.4（关卡3.4.0；接口与Schema 1.4.0）灰盒已按独立 QA 联合证据接受并 SOURCE STOP。v3.4 增加三级服务器提示、本局统计和通关结算，没有引入 Phaser 或最终美术。QA 结果及限制见 [`v3.4 QA 结果`](evidence/upgrade/v3.4/qa/result.json)、[`v3.4 独立报告`](review/findings/upgrade-v34.md) 和 [`升级交付门槛`](release/UPGRADES.md)。v3.4 commit `49a2f925a78055552781685e79ee96496bb9bdd6` 和 tag `v3.4-graybox-complete` 已推送并由 GitHub API 核实，作者与提交者均关联到 `liy222`。多时刻存档增量已按独立 QA 联合证据验收：可为不同进度分别命名并选择读取，重新开始保留存档。验收与限制见 [`多存档验收`](evidence/integration/multiple-saves/accepted.json) 和 [`独立报告`](review/findings/multiple-saves.md)。前一版本 v3.3 的 commit `58587cf9458920fef435e8cb5d7638b1e318c19b`、tag `v3.3-mini-games` 已推送并核实。设计基线见 [`docs/upgrade-plan.md`](docs/upgrade-plan.md)；更早版本的交付信息见 [`升级交付门槛`](release/UPGRADES.md)。

## 当前升级路线

v3.3 API 联合验收包括首轮全套105 passed、291个子项通过，及1个 QA 尾部断言错误；该方法按 Main 指示修正预期后定向复验为1 passed、3个子项通过。旧97项与新增9个方法由两个运行联合覆盖；没有第二次全套 exit 0，也不表述成106 passed。修复前后27个产品候选文件匹配。Chrome exit 0、102项、issues为空、6张截图已目视检查；build exit 0，均绑定同一候选。根目录 CMD 仅作字节/配置检查，没有实际启动。详情见 [`v3.3 QA 结果`](evidence/upgrade/v3.3/qa/result.json) 与 [`v3.3 独立报告`](review/findings/upgrade-v33.md)。

v3.4 API 联合验收保留首轮全套 exit 1：118个测试方法通过、315个子项通过，1个子项因 QA 预期错误失败；问题是并发期间相同提示请求实际按既有 reservation 规则返回503 `MODEL_UNAVAILABLE`，QA 原预期为409。仅该新方法修正预期后定向复验 exit 0，1个方法、3个子项通过；这不等于第二次全套118项通过。首轮完整运行与定向复验联合覆盖，不相加重复子项。候选38个源码/合同/规格/launcher路径执行阶段及最终哈希均一致。独立 build exit 0；Chrome exit 0、132项检查、issues为空，6张截图已检查；launcher 字节/配置检查 exit 0，但未实际启动根目录 CMD。完整边界见 [`v3.4 QA 结果`](evidence/upgrade/v3.4/qa/result.json) 与 [`v3.4 独立报告`](review/findings/upgrade-v34.md)。

v3.2 独立 API QA exit 0：97 passed、257 个子项通过、1 个弃用警告；旧89项和新增8个测试方法通过。覆盖46步三房间路线、各设备与物品槽阶段的保存/重置/恢复/Store 重开、错误尝试、跨版本快照拒绝，以及 AI 读取边界（12类伪造读取均被拒绝）。修复前候选的 Chrome 检查 exit 0（61项）和前端构建 exit 0被保留复用；它们不是修复后源码的重复运行。实际根目录启动 CMD 未运行，仅做字节与配置检查。具体范围、来源和限制见 [`v3.2 QA 结果`](evidence/upgrade/v3.2/qa/result.json) 与 [`独立报告`](review/findings/upgrade-v32.md)。QA 使用合成 AI fixture，没有真实 provider/网络调用；不代表真人试玩或20–30分钟游玩时长验收。

v3.0 已完成并标记为 `v3.0-gameplay-information`。v3.4 三级提示、统计、结算与完整路线灰盒已按联合证据完成独立 QA。按用户指示，进入画面升级前暂停，等待详细计划；目前没有 Phaser 或最终美术。

## 双击启动当前版本 v3.4

在 Windows 文件资源管理器中双击仓库根目录的 `启动游戏.cmd`，默认以免费 `mock` Provider 和独立的 `./data/game-v3.4.sqlite` 启动当前 v3.4 候选。服务运行期间不要关闭窗口，按 Ctrl+C 停止。若启动失败，窗口会保留错误信息和退出码；缺少 Python 或依赖、端口已占用时按提示处理。启动器不会自动安装或升级依赖，也不会结束已占用端口的进程。可右键该文件创建 Windows 快捷方式。

首次运行前按下方首次安装依赖步骤安装依赖；此后可直接双击启动。

## 游戏内选择 AI 探索伙伴

启动游戏后，可在“AI 探索伙伴”中选择免费模拟或真实 DeepSeek。免费模拟是默认选项，不会调用真实模型。v3.4 的提示级别选择只在本地生效；只有点击“获取提示”才会发起请求，也不会代替玩家执行行动。真实模式下，v3.4 只向 DeepSeek 发送符合条件的提示主题名称和已发现线索 ID，不发送玩家问句、对话历史或线索全文；旧版本助手仍按各自原有行为处理。选择真实 DeepSeek 后，在密码输入框中手动填写 API Key；填写本身不会发起请求。真实请求按该 API 账户规则计费；QA 没有进行付费调用，选择真实模式也不会重置项目现有共享预算或账本。

手动输入的 Key 只保留在当前页面的 React 内存中，不写入存档；刷新页面、切回免费模拟、切换游戏会话或重新开始都会清除它。日常游玩无需编辑 `启动游戏.cmd` 或 `.env`。通过命令行启动的原有 `--provider` 与 `.env` 配置仍供本地开发使用，README 中的双击启动示例继续使用免费模拟模式。

## 本地启动当前版本 v3.4

首次安装依赖或修复缺失依赖时，在 Windows PowerShell 中从仓库根目录执行。使用指定 Conda Python，不创建或重置环境；平时可直接双击上方启动器：

```powershell
Set-Location -LiteralPath 'D:\深度能力'
$ProjectPython = 'C:\Users\liyh\.conda\envs\1\python.exe'
& $ProjectPython -m pip install -r backend/requirements.lock.txt
npm.cmd --prefix frontend ci
$env:GAMEPLAY_VERSION = 'upgrade'
$env:SQLITE_PATH = './data/game-v3.4.sqlite'
& $ProjectPython -m scripts.dev --provider mock
```

默认工作版本使用独立的 `game-v3.4.sqlite` 与 v3.4 会话存储命名空间。显式设置 `GAMEPLAY_VERSION` 为 `v3.3`、`v3.2`、`v3.1` 或 `legacy`，并分别选择对应的 `game-v3.3.sqlite`、`game-v3.2.sqlite`、`game-v3.1.sqlite` 或 `game-v2.sqlite`，可运行保留版本；各模式使用独立浏览器会话空间，不自动迁移。首次安装依赖后，日常启动可从设置 `GAMEPLAY_VERSION` 和 `SQLITE_PATH` 的两行开始。服务启动后打开 <http://127.0.0.1:5173/>；开发启动器会同时启动前后端并检查本地健康页。按 Ctrl+C 停止两项服务。

## 使用同代码运行历史 v2 基线

如需继续 v2 进度，在新的 PowerShell 窗口显式选择 legacy，并使用 v2 数据库：

```powershell
Set-Location -LiteralPath 'D:\深度能力'
$ProjectPython = 'C:\Users\liyh\.conda\envs\1\python.exe'
$env:GAMEPLAY_VERSION = 'legacy'
$env:SQLITE_PATH = './data/game-v2.sqlite'
& $ProjectPython -m scripts.dev --provider mock
```

legacy 使用原 `campus-lab-session-v1` 浏览器存储；v3.1 使用独立的 `campus-lab-session-upgrade-v3.1`。两种模式不会删除或迁移对方的 session token、存档或数据库。不要在同一服务进程中混用版本与数据库路径。

如需在本 PowerShell 窗口中清除变量，停止服务后执行：

```powershell
Remove-Item Env:GAMEPLAY_VERSION,Env:SQLITE_PATH -ErrorAction SilentlyContinue
```

游戏界面可以在当前游戏中创建多个存档，每次创建都增加一份，列表显示名称、时间、房间、线索数和进度状态；选择“读取”并确认后，当前进度会替换为所选时刻。名称可选，留空时由系统命名。存档列表保留旧版单槽记录；“旧版单槽兼容操作”中的保存会替换那一份旧存档，不会替换上方独立存档。重新开始会清空当前进度但保留存档。存档属于本机当前游戏，不提供账号或云端同步；同一标签页刷新或本地服务重启后可继续读取。T30 曾验证旧单槽的恢复及 v2 与归档 v1 快照的版本隔离。数据库属于本地运行数据，不是发布材料。

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
- 交付文档本次整理记录：[`evidence/delivery/T31-docs-20261005/report-v6.json`](evidence/delivery/T31-docs-20261005/report-v6.json)（前次修订在 `report-v2.json`，原始记录在 `report.json`，均保留）。

<details>
<summary>历史交付证据（不代表当前 v3.3 升级版本）</summary>

截至 2026-10-06 的历史证据仍有明确边界。`CH01_v2`（commit `242ecfc4d9f7bf1a8480508de701d9efc7822fe7`）与 v1 回退 commit `7821af4efe0613c20a80ea164c1dab1c0f288bab` 有独立源清单和本地数据库。Main 对 commit `833aafb09ad20dc1ba82cfed198485ce13300067` 的新源码目录复现 exit 0，10,778 文件逐字节匹配，8项外层检查及3项评价器precheck均通过；独立只读复核 10,842/10,842、exit 0，另有2项静态补充说明。范围仍是当时的 Windows/Conda，不是新OS/新Python环境。E1 continuation 命令 exit 0，49计划项中48调用、47返回、1项 `MODEL_UNAVAILABLE` 用量未知、1项未调用；原22完成和1超时没有重放。新数据独立合并复核最终路径 `evidence/qa/T25-merged-20261005T160549469322Z/result.json` 为1427/1427、exit 0、STOP：69/72有终态、34个完整配对，另外2 failed、1 not_called；结论不支持完整三重复或统计优胜。最新Main快照为101 settled calls、保守上界¥0.81685848、cap ¥10、pending 0、frozen 0；新8次评价器调用的已知用量¥0.1484352为调用元数据，不是供应商发票。原K1/K2记录维持10/11。之后旧6项批准载荷各调用一次：K4模型有效且按预期判FAIL；E1两条与CH01三条为 `INSUFFICIENT_EVIDENCE`，保留原结论且不可重发。提示版本2e977的8项新载荷（校准3、E1 2、CH01 3）各调用一次，独立 QA 75/75 SOURCE STOP。校准11/11由3条付费判读与8项确定性对照构成；E1原登记批次判读2条PASS，但对应的72计划状态仍为22 completed、1 timeout、49 not_called，不能写成72完成；CH01三条PASS限于当时冻结工程 Claim。CH01 v3身份/别名检查79/79通过，但不等于真实语义验收。没有真人试玩、玩家决策或人类/教师签署；没有公开部署。
</details>
