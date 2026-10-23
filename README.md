# 逃离校园实验室

V5 目前是未发布的开发候选，启动、隔离与有限验证范围见本页末尾的 [V5 说明](#v5-开发候选未发布验收)。

这是一个本地运行的三房间解谜游戏：规则由后端执行，AI 队友提供受限帮助；旧版本中的推进建议须由玩家确认。当前画面版本为 v4.2：三个房间均使用 Phaser 4.2.1 Canvas、固定视角点选和局部特写；v4.2-handpainted 增量已将80张手绘状态/特写物件图与5张净背景接入运行画面，原有84项 SVG 保留，并加入全屏结算、静音与减少动画选项、缺失素材重试和按需加载。另经 stage-ui 版式修正，将桌面 HUD、背包和操作控件置于 Canvas 画框内，窄屏表单作为场景内面板显示；legacy 入口保留且与默认视觉入口互斥。Room 3 终检控制台本轮修复已验证：即使 access_card 仍选中，也能打开已插入纸条的控制台、填写四个按钮，并通过控制台显式启动 FINAL_CHECK；服务器提交校验与答案不变，同版本存档兼容。服务重启后刷新页面即可使用。详情见[终检控制台修复验收](evidence/integration/panel-submit/accepted.json)。最新 closeup-panel 修正清理切换特写时的旧交互区域：背景不可点，当前热点和柜体/托盘内合法物品仍可操作；Room 3 插入 research_strip 后立即显示四台设备图形并允许本地编辑草稿，最终提交仍须进入 FINAL_CHECK。三房间特写不再显示重复的“观察”按钮；点击物品仍会触发观察，目镜等专用观察热点保留。游戏规则关卡仍为3.4.0，接口与 Schema 仍为1.4.0，原有启动器、AI 和多时刻本地存档继续使用。v4.2 联合 QA 的范围与限制见 [`v4.2 验收记录`](evidence/upgrade/v4.2/accepted.json)、[`v4.2 独立 QA 报告`](evidence/upgrade/v4.2/qa/result.json) 和 [`升级交付门槛`](release/UPGRADES.md)。v4.2 commit `74f6272b9204f352a6b598d3bd4273452f8184be` 与 tag `v4.2-final-rusty-visual` 已推送核实，GitHub 作者与提交者均为 `liy222`。v4.1 commit `161d3e6f25406d44eb55c48c295b86c7289d8f2c` 与 tag `v4.1-room2-rusty-visual` 已推送核实，GitHub 作者与提交者均为 `liy222`。v4.0 commit `1047e293ade70e446c9c76be0a0d751f3e3ad81a` 与 tag `v4.0-room1-rusty-visual` 已推送并核实，GitHub 作者与提交者均为 `liy222`。v3.4 commit `49a2f925a78055552781685e79ee96496bb9bdd6`、tag `v3.4-graybox-complete` 与多时刻存档增量 commit `8e491d7c4b4972cb4a3972627fde3a5fc98c28ee`、tag `v3.4-multiple-saves` 已推送并核实，作者与提交者均为 `liy222`。多时刻存档可分别命名并选择读取，重新开始会保留存档；验收见 [`多存档验收`](evidence/integration/multiple-saves/accepted.json) 和 [`独立报告`](review/findings/multiple-saves.md)。主要画面基线见 [`docs/visual-plan.md`](docs/visual-plan.md)，历史玩法升级规划见 [`docs/upgrade-plan.md`](docs/upgrade-plan.md)；更早版本的交付信息见 [`升级交付门槛`](release/UPGRADES.md)。

v4.2-handpainted 已通过独立联合定向 QA：85张 PNG 静态核对87项 exit 0，前端构建52个模块、2.98秒、exit 0（仍有既有 Phaser 大包警告）。浏览器证据由多个范围组成：首轮201条记录在 R1/R2 和早期 R3 CARD_ACCEPTED 后因 QA 选中物品适配器断言失败而 exit 1；随后窄范围101条 exit 0、issues为空，另有75条 exit 0 的胜利页展示检查。计数未相加，也不是一次全程浏览器全绿。联合范围覆盖实际 R1/R2 与早期 R3、fixture 准备后的 R3 终检至 EXIT/胜利、多存档选择、刷新、一次后端进程重启、触屏/键盘、PNG 重试与按需加载。规则关卡3.4.0、API/Schema 1.4.0、AI和多时刻本地存档保持。QA 使用独立新数据库；没有重跑完整后端套件、启动根目录 CMD、OS 重启、付费模型调用或真人通关时间验收。详情见 [`手绘接入验收`](evidence/integration/handpainted/accepted.json)、[`QA 结果`](evidence/integration/handpainted/qa/result.json) 和 [`素材/元数据交付记录`](evidence/integration/handpainted/assets/report.json)。手绘接入提交 `041514d1691353deea8a52bfb2206f3678207c3c` 与标签 `v4.2-handpainted` 已推送至私有远端并核实，GitHub 作者与提交者均为 `liy222`。

## 当前升级路线

v3.3 API 联合验收包括首轮全套105 passed、291个子项通过，及1个 QA 尾部断言错误；该方法按 Main 指示修正预期后定向复验为1 passed、3个子项通过。旧97项与新增9个方法由两个运行联合覆盖；没有第二次全套 exit 0，也不表述成106 passed。修复前后27个产品候选文件匹配。Chrome exit 0、102项、issues为空、6张截图已目视检查；build exit 0，均绑定同一候选。根目录 CMD 仅作字节/配置检查，没有实际启动。详情见 [`v3.3 QA 结果`](evidence/upgrade/v3.3/qa/result.json) 与 [`v3.3 独立报告`](review/findings/upgrade-v33.md)。

v3.4 API 联合验收保留首轮全套 exit 1：118个测试方法通过、315个子项通过，1个子项因 QA 预期错误失败；问题是并发期间相同提示请求实际按既有 reservation 规则返回503 `MODEL_UNAVAILABLE`，QA 原预期为409。仅该新方法修正预期后定向复验 exit 0，1个方法、3个子项通过；这不等于第二次全套118项通过。首轮完整运行与定向复验联合覆盖，不相加重复子项。候选38个源码/合同/规格/launcher路径执行阶段及最终哈希均一致。独立 build exit 0；Chrome exit 0、132项检查、issues为空，6张截图已检查；launcher 字节/配置检查 exit 0，但未实际启动根目录 CMD。完整边界见 [`v3.4 QA 结果`](evidence/upgrade/v3.4/qa/result.json) 与 [`v3.4 独立报告`](review/findings/upgrade-v34.md)。

v3.2 独立 API QA exit 0：97 passed、257 个子项通过、1 个弃用警告；旧89项和新增8个测试方法通过。覆盖46步三房间路线、各设备与物品槽阶段的保存/重置/恢复/Store 重开、错误尝试、跨版本快照拒绝，以及 AI 读取边界（12类伪造读取均被拒绝）。修复前候选的 Chrome 检查 exit 0（61项）和前端构建 exit 0被保留复用；它们不是修复后源码的重复运行。实际根目录启动 CMD 未运行，仅做字节与配置检查。具体范围、来源和限制见 [`v3.2 QA 结果`](evidence/upgrade/v3.2/qa/result.json) 与 [`独立报告`](review/findings/upgrade-v32.md)。QA 使用合成 AI fixture，没有真实 provider/网络调用；不代表真人试玩或20–30分钟游玩时长验收。

v3.0 已完成并标记为 `v3.0-gameplay-information`。v3.4 三级提示、统计、结算、完整路线灰盒及多时刻存档均已按联合证据接受。v4.0–v4.2 三房间视觉升级与最终界面已由联合 QA 接受；v4.2 视觉版本 commit `74f6272b9204f352a6b598d3bd4273452f8184be` 与 tag `v4.2-final-rusty-visual` 已推送核实。stage-ui 版式修正也已由联合 QA 接受，修正 commit `68693a5fc36b16e21b9323e89145ca3195294499` 与 tag `v4.2-stage-ui` 已推送核实，作者与提交者均为 `liy222`。closeup-panel 已由定向联合 QA 接受，修正 commit `c76e77ec9129f32606bb5dee225621cae154427d` 与 tag `v4.2-closeup-panel` 已推送核实，GitHub 作者与提交者均为 `liy222`；重启服务并刷新页面即可使用，现有存档无需重开。当前状态和 QA 边界见 [`stage-ui 验收记录`](evidence/integration/stage-ui/accepted.json) 与 [`closeup-panel 验收记录`](evidence/integration/closeup-panel/accepted.json)。

## 双击启动当前游戏规则版本 v3.4

在 Windows 文件资源管理器中双击仓库根目录的 `启动游戏.cmd`，默认以免费 `mock` Provider 和独立的 `./data/game-v3.4.sqlite` 启动当前 v3.4 候选。服务运行期间不要关闭窗口，按 Ctrl+C 停止。若启动失败，窗口会保留错误信息和退出码；缺少 Python 或依赖、端口已占用时按提示处理。启动器不会自动安装或升级依赖，也不会结束已占用端口的进程。可右键该文件创建 Windows 快捷方式。

首次运行前按下方首次安装依赖步骤安装依赖；此后可直接双击启动。

## 游戏内选择 AI 探索伙伴

启动游戏后，可在“AI 探索伙伴”中选择“预设提示（免费）”或“AI 伙伴（真实模型）”。v3.4 默认使用免费的预设提示，不调用真实模型；选择 L1、L2 或 L3 后无需输入问题，点击“获取提示”即可。提示强度只影响免费预设。旧版本界面仍显示免费模拟和真实 DeepSeek，按各自原有行为处理。

真实 AI 伙伴需填写 API Key 和自然语言问题。每次请求会结合当前问题、最近3轮成功伙伴问答、最近3条不含参数的动作摘要、相关的已发现证据与当前公开进度，目标是简短讨论；伙伴不会代替你操作，也不会直接给出完整答案。普通数字或背景问题可以交流；明确请求判定整组答案对错或核对完整答案时，界面显示本地提醒，不调用模型，也不增加提示次数。经校验的伙伴帮助会计入提示次数，但不会修改免费预设提示当前等级。防剧透识别是启发式，不能保证识别所有隐晦答案或事实错误。当前页面最多展示最近4轮交流；刷新后页面历史清空，但同一游戏进度下的后端上下文仍可能保留最近3轮。读取存档会创建新游戏进度并隔离此前上下文。当前页历史展示会遮住误粘贴的问题中的 API Key 或会话令牌。

手动输入的 Key 只保留在当前页面内存中，不写入存档；刷新页面、切回免费预设、切换游戏会话或开始新游戏都会清除。真实请求按你自己的 API 账户规则计费；先前 UI QA 未调用付费模型，后续定向真实试玩见下方记录。选择真实模式不会重置项目现有共享预算或账本。日常游玩无需编辑 `启动游戏.cmd` 或 `.env`；命令行 `--provider` 与 `.env` 仍供本地开发使用。先前 UI 范围见 [AI 伙伴验收](evidence/integration/ai-companion/accepted.json) 与 [独立 QA 结果](evidence/integration/ai-companion/qa/result.json)。

## 本地启动当前游戏规则版本 v3.4

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

当前游戏可创建多个本地存档；每份可单独命名，列表显示名称、时间、房间、线索数和进度状态。选择“读取”并确认后，当前进度切换到所选时刻。选择“删除”会先显示存档名称和不可恢复提示；确认后只删除该份存档，不影响当前游戏进度。取消或按 Escape 不会删除。重新开始会清空当前进度，但保留已有存档；已有存档仍可读取。存档保存在本机并关联当前游戏会话，不提供账号或云端同步；刷新当前标签页或重启本地服务后仍可读取。临时输入和顺序草稿不会写入存档，读取或刷新后需重新填写。T30 曾验证旧单槽恢复及 v2 与归档 v1 快照的版本隔离。

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


真实模型定向试玩共8次：首批7次与一次窄修后的 C08；首批只有 C03、C07 通过全部适用质量项，C01/C02 有事实问题，C04 被引用保护拦截，C05/C06 的引用不足以支持回答。C08 返回了柜体状态与目录相关内容、空引用，但措辞较直接且仍带有 `CODE_ACCEPTED` 状态字样；不能据此称整体质量通过，首轮其余问题场景未全部真实复测。8次按账本 usage 与既有峰值价格计算的计费上界为 ¥0.020108，累计上界 ¥0.89436648；这是保守上界，不是供应商账单。审查结论与限制见 [真实试玩验收](evidence/integration/ai-companion-real/accepted.json)、[最终 QA 复核](evidence/integration/ai-companion-real/qa/final-review.json) 和[独立发现记录](review/findings/ai-companion-real.md)。

本轮 AI 伙伴质量修正仅获有限接受：新的 strict JSON mode 与上下文减噪后，唯一真实 Q05 登录样本通过适用质量项；Q01/Q03 因非 JSON 被拦、Q02 跳过、Q04 的无依据旧线索联系均保留为未接受结果。离线验证来自两个源码阶段，不能合并成同一候选全绿；尚未验证连问、柜体/线路新候选真实质量或真人体验。详情见 [独立 QA 结论](evidence/integration/ai-companion-quality/qa/final-review.json) 与[发现记录](review/findings/ai-companion-quality.md)。
2026-10-18：AI 伙伴 next-step 修复完成定向回归与构建；真实两轮问答均正常交付，最后的模型用词调整仅离线核对，不构成全面质量认证。重启一键启动器后生效，现有存档可继续使用，无需重开。N02 的“观察”按钮措辞仍属弱项；未保存的旧拒绝回复具体触发原因未知。详见[独立 QA 限定结论](evidence/integration/companion-nextstep/qa/final-review.json)。

## V5 开发候选（未发布验收）

V5 是与经典版本并存的本机开发候选，尚未达到发布验收。新版默认使用 `data/game-v5.sqlite`，不会迁移或复用旧库；旧入口 [`启动游戏.cmd`](启动游戏.cmd) 与 `data/game-v3.4.sqlite` 保留。新版入口是 [`启动新版.cmd`](启动新版.cmd)，生产预览固定为 `http://127.0.0.1:8001/`，须先构建 `frontend/dist-v5/`。开发模式在 `127.0.0.1:5174/`，从项目 Python 启动：

```powershell
$env:PYTHONUTF8 = '1'
& 'C:\Users\liyh\.conda\envs\1\python.exe' -B -X utf8 -m scripts.run_v5 --dev --open-browser
```

手动构建新版前端：

```powershell
$env:VITE_GAMEPLAY_VERSION = 'v5'
npm.cmd --prefix frontend run build
```

V5 本机私人账户不是云账户。经典玩法、已经生成的关卡和免费提示不需要 Key；新关卡生成才需要临时输入 BYOK。生成失败不会自动重试并产生额外付费调用。启动器不会安装依赖、自动构建、删除旧数据或结束占用端口的其他进程；QA 临时库选项只用于隔离验证。完整启动细节见 [`release/V5.md`](release/V5.md)。

离线独立验证只对记录的候选与范围成立：共覆盖 38 个网页动作、归档与恢复、重载和后端进程重启，以及 3 个浏览器视口的布局检查；不同源码阶段的定向检查不相加为一次全绿。四项定向发现均已关闭，详见[离线联合复核](review/findings/v5-offline-joint.md)和[离线结果](evidence/upgrade/v5.0/qa/final-offline-result.json)。这不证明真实生成质量或整体发布验收。

第一轮真实样本运行实际调用模型 3 次，G1/G2/G3 均被拒绝，A1/A2 跳过；保守用量上界增量 ¥0.03128048（非供应商账单），原有 3 条未知调用保持未知。结果见[第一轮记录](evidence/upgrade/v5.0/real-samples/result.json)和[独立复核](review/findings/v5-real-samples-review.md)。第二轮经明确授权后实际调用模型 4 次：G1 为 1/easy 单房间关卡，实际通过 8 个动作到 EXIT；G2/G3 被拒绝；A1 因模型复用了公开资料标题中的 clue IDs 而被内容 guard 拒绝，A2 跳过。该轮保守用量上界增量 ¥0.03340072（非供应商账单），见[第二轮记录](evidence/upgrade/v5.0/real-samples-round2/result.json)、[执行复核](evidence/upgrade/v5.0/real-samples-round2/main-execution-review.json)和[独立复核](review/findings/v5-round2-real-review.md)。两轮来自不同源码候选，分别记为第一轮 0/3 与第二轮 1/3 生成样本，不能合并或外推为多房间生成质量、真实伙伴成功或 GEN-01 验收。其后仅 AI 投影的 403-source 候选通过指定 8 项窄离线检查（exit 0）；该检查含合成 MockTransport，不是新的真实复测。原始 A1 仍被拒、A2 未使用；没有额外真实调用授权。该窄结果与限制见[QA sealed result](evidence/upgrade/v5.0/qa/round2-ai-fix-result.json)及[独立复核](review/findings/v5-round2-ai-fix.md)。

AI-only 窄离线检查保留了公开 clue refs 与原始事实，通过公开物件名称改善伙伴措辞；原 A1 实际答复仍未成功送达，不能声称真实伙伴成功。合成伙伴请求保守上界为 0.046688 元（在 0.05 元上限内）；2000 字全四字节 Unicode 生成预算上界为 0.212808 元，超过单次 0.20 元上限，已验证会在发送/预留前拒绝。评价器 C1/C2/C3 有限声明登记已通过（53 个源码文件、9 个登记产物）；CLI precheck 为 READY，但确定性判读为 3 项 `INSUFFICIENT_EVIDENCE`，并非产品测试失败，也不代表 PASS。付费评价因 3 条历史未知调用而严格阻塞；没有真实模型判读时，不将任何声明标为 PASS。其他已知限制：两个冷启动标签页都没有 Cookie 时可能需要手动刷新；当前素材目录较通用，并非大量定制校园美术。当前没有 V5 发布 tag、合并到 main 或部署。
