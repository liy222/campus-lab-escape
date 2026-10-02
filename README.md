# 逃离校园实验室

本地网页 AI 解谜游戏。M0 工程骨架已接受，提供 React 页面、FastAPI 健康检查和统一启动/检查入口；R1 游戏接口与界面处于候选实现阶段，尚待独立 QA。当前已接受版本与证据入口见 `STATUS.md` 和 `evidence/index-M0.json`。完整范围见 `docs/SPEC.md` 与 `docs/execution-plan.md`，规格和候选代码不代表验收通过。

## 环境与安装

在 PowerShell 中使用指定现有 Python 环境，无需新建或重置环境：

```powershell
Set-Location -LiteralPath 'D:\深度能力'
$ProjectPython = 'C:\Users\liyh\.conda\envs\1\python.exe'
& $ProjectPython --version
& $ProjectPython -m pip install -r backend/requirements.lock.txt
npm.cmd --prefix frontend ci
```

本次实际环境为 Windows、Python 3.14.7、Node 24.17.0、npm 11.13.0。Python 锁文件只包含项目所需依赖闭包，前端由 `frontend/package-lock.json` 锁定。环境安装及验证记录在 `evidence/environment/delivery-*`。

## 启动与停止

```powershell
& $ProjectPython -m scripts.dev --provider mock
```

启动后打开 <http://127.0.0.1:5173/>，后端健康检查为 <http://127.0.0.1:8000/api/health>。前端 `/api` 请求代理到后端。当前工作区包含 R1 候选游戏页面：点击“开始新游戏”创建会话；之后可点“同步进度”或刷新页面，在当前浏览器标签页继续游戏。若当前已有会话，再开新游戏会先询问确认；确认后当前标签页切换到新会话，旧会话不能从该标签页恢复。进度关联浏览器标签页，不是服务端存档。

选择场景物件后，按页面提供的操作查看、拾取或使用道具。密码框只接受 1–16 位数字；提交错误密码时页面显示服务端返回的错误信息，可根据已发现线索修正后再试。服务异常时可用“同步进度”核对服务器当前状态。

在启动窗口按 **Ctrl+C** 统一停止两个服务。任一服务意外退出时，脚本会停止另一个服务并返回失败。端口占用会明确报错；可使用 `--backend-port 8001 --frontend-port 5174` 调整。服务仅监听本机。

启动脚本读取项目根目录 `D:\深度能力\.env`，文件每行使用 `KEY=VALUE`；允许空行、整行 `#` 注释和一对包围值的引号，不支持多行值、`export` 或重复键，也不会执行 Shell 语法或展开变量。已有进程环境变量优先；`--provider mock` 显式覆盖 Provider，因此上方启动命令仍用于 mock 验证。省略 `--provider` 时使用加载后的 `AI_PROVIDER`，未设置则为 mock。启动日志不打印配置值。

用户选择 DeepSeek 4.1 Flash，根目录 `.env` 本地配置项为 `AI_PROVIDER=deepseek`、`MODEL_BASE_URL=https://api.deepseek.com`、`MODEL_NAME=deepseek-flash`、`MODEL_API_KEY=本地密钥`；可参考 `.env.example`。若要配置，将此组值写入项目根目录 `.env`，并仅在本机填入 API 密钥。人民币 10 元项目总预算已获授权，涵盖所有付费调用；当前 R1 候选尚未集成真实 AI，网页中的 AI 区域显示“尚未开放”，因此不能据此配置或启动真实模型调用，也不能宣称模型可用。当前没有真实模型调用验收证据。不要把 API 密钥放入前端变量、证据或仓库。

`.env` 只加载到后端子进程。前端 npm/Vite 使用单独的环境，剥离继承的模型配置及名称含 API_KEY、TOKEN、SECRET 等敏感标识的变量，仅添加本地后端代理地址。

R1 后端候选提供创建会话、读取状态和手动动作接口；它使用本项目 `data/game.sqlite` 持久化数据，可用服务端环境变量 `SQLITE_PATH` 改到独立位置。能力令牌仅在创建会话响应中返回，不能复制到证据或日志。AI 区域、保存进度、恢复存档和重新开始按钮目前禁用；不要把契约中的接口或配置项当成这些网页功能已开放。

## 构建与确定性检查

```powershell
npm.cmd --prefix frontend run build
& $ProjectPython -m scripts.check --suite deterministic --output evidence/runs/check
```

统一检查实际执行前端构建和 `tests/` 中的 pytest 测试，设置 mock Provider 和独立临时数据库路径。每次生成新的证据子目录，保存命令、退出码、输出摘要文件、源文件和日志 SHA-256。没有测试目录时 pytest 退出码为 4，没有收集到测试时为 5，均为检查失败；不会把空测试视为通过。日志若包含真实密钥或会话令牌，应先脱敏再提交。运行期间源码发生变化也会失败；正式 QA 应在稳定候选版本执行。

## 数据重置

先停止服务。必须显式指定本项目 `data/` 范围内的目录，省略确认参数只预览：

```powershell
& $ProjectPython -m scripts.reset --data-dir '.\data'
& $ProjectPython -m scripts.reset --data-dir '.\data' --confirm
```

确认后删除该目录中的 `game.sqlite`、`game.sqlite-wal`、`game.sqlite-shm`，清除该数据库中的所有会话和存档。其他文件、项目外路径、符号链接或目录联接均会拒绝；不会删除 Python 环境。若设置了其他数据库位置，不要把此命令用于项目外目录；请先核对数据库归属。保存与恢复流程尚待实现和独立验证。

## 当前验证范围与限制

当前独立 R1 浏览器 QA 仍在进行；已有运行记录和失败批次见 `evidence/qa/`，不能据此声称浏览器验收通过。后端 QA 有实际运行报告，范围与限制见交付索引。完整手动通关、保存/恢复/重置网页流程、真实 AI、实验、CH01、干净目录交接及真人课程签署尚无完成证据。当前不可声明项目完成或发布通过。没有公开部署或 GitHub Actions。

## 交付材料索引

按六类查看当前材料与未完成项：[`release/README.md`](release/README.md)。M0 正式基线证据入口为 [`evidence/index-M0.json`](evidence/index-M0.json)；尚未生成 R1 正式发布清单。
