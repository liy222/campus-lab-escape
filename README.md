# 逃离校园实验室

本地网页 AI 解谜游戏。当前工程骨架提供 React 页面、FastAPI 健康检查和统一启动/检查入口；三房间游戏、存档与 AI 交互尚未在此版本实现。正式执行范围见 `docs/execution-plan.md`，计划不代表已完成。

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

启动后打开 <http://127.0.0.1:5173/>，后端健康检查为 <http://127.0.0.1:8000/api/health>。前端 `/api` 请求代理到后端。当前首页只显示工程状态。

在启动窗口按 **Ctrl+C** 统一停止两个服务。任一服务意外退出时，脚本会停止另一个服务并返回失败。端口占用会明确报错；可使用 `--backend-port 8001 --frontend-port 5174` 调整。服务仅监听本机。

`.env.example` 是服务端配置示例，启动脚本不会自动读取 `.env`。目前使用 `mock`，未进行真实模型调用；开发 Agent 模型不代表游戏 API 模型。不要把 API 密钥放入前端变量或提交到仓库。

## 构建与确定性检查

```powershell
npm.cmd --prefix frontend run build
& $ProjectPython -m scripts.check --suite deterministic --output evidence/runs/check
```

统一检查实际执行前端构建和 `tests/` 中的 pytest 测试，不调用付费模型。每次生成新的证据子目录，保存命令、退出码、输出摘要文件、源文件和日志 SHA-256。测试尚未提供或没有收集到测试时会真实失败，不能将工程骨架视为正式验收通过。运行期间源码发生变化也会失败；正式 QA 应在稳定候选版本执行。

## 数据重置

先停止服务。必须显式指定本项目 `data/` 范围内的目录，省略确认参数只预览：

```powershell
& $ProjectPython -m scripts.reset --data-dir '.\data'
& $ProjectPython -m scripts.reset --data-dir '.\data' --confirm
```

确认后删除该目录中的 `game.sqlite`、`game.sqlite-wal`、`game.sqlite-shm`，清除游戏和存档。其他文件、项目外路径、符号链接或目录联接均会拒绝；不会删除 Python 环境。此骨架尚未创建游戏数据库，保存与恢复流程待实现验证。

## 当前验证范围与限制

交付 Owner 的局部验证是工程验证，独立 QA、完整手动通关、界面试玩、真实 AI、实验、CH01、干净目录交接及真人课程签署均需各自真实证据。当前不可声明项目完成或发布通过。没有公开部署或 GitHub Actions。
