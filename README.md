# 逃离校园实验室

本地网页解谜游戏。M0 与 M1/R1 已验收；M2 手动范围现已通过独立 API、浏览器和综合 deterministic checker，证据见 `release/README.md` 与 `evidence/delivery/docs-index-M2-accepted-20261002.json`。M2 包含三房间手动通关及单槽保存、恢复、重置。游戏 AI 尚未开放。完整范围见 `docs/SPEC.md` 与 `docs/execution-plan.md`；M2 验收不代表项目整体完成。

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

启动后打开 <http://127.0.0.1:5173/>，后端健康检查为 <http://127.0.0.1:8000/api/health>。前端 `/api` 请求代理到后端。当前实现包含三房间手动游戏，可在 R1/R2/R3 探索并通关至 EXIT，也可使用网页单槽保存、恢复和重置。重置清除当前游戏进度但保留存档。点击“开始新游戏”创建会话；之后可同步或刷新当前浏览器标签页。

选择场景物件后，按页面提供的操作查看、拾取或使用道具。密码框只接受 1–16 位数字；提交错误密码时页面显示服务端返回的错误信息，可根据已发现线索修正后再试。服务异常时可用“同步进度”核对服务器当前状态。

在启动窗口按 **Ctrl+C** 统一停止两个服务。任一服务意外退出时，脚本会停止另一个服务并返回失败。端口占用会明确报错；可使用 `--backend-port 8001 --frontend-port 5174` 调整。服务仅监听本机。

启动脚本读取项目根目录 `D:\深度能力\.env`，文件每行使用 `KEY=VALUE`；允许空行、整行 `#` 注释和一对包围值的引号，不支持多行值、`export` 或重复键，也不会执行 Shell 语法或展开变量。已有进程环境变量优先；`--provider mock` 显式覆盖 Provider，因此上方启动命令仍用于 mock 验证。省略 `--provider` 时使用加载后的 `AI_PROVIDER`，未设置则为 mock。启动日志不打印配置值。

用户选择 DeepSeek 4.1 Flash，根目录 `.env` 本地配置项为 `AI_PROVIDER=deepseek`、`MODEL_BASE_URL=https://api.deepseek.com`、`MODEL_NAME=deepseek-flash`、`MODEL_API_KEY=本地密钥`；可参考 `.env.example`。真实凭据未在此处读取或展示。人民币 10 元项目总预算已获授权，涵盖所有付费调用。独立 Provider adapter 的工具请求与结果回传已通过验证，报告记录 4 次请求，累计计费上限估算为 ¥0.00230824；账单尚未核实。该验证不包含游戏 AI 集成：游戏 AI 仍未集成、网页中仍显示“尚未开放”，当前不可用。不要把 API 密钥放入前端变量、证据或仓库。

`.env` 只加载到后端子进程。前端 npm/Vite 使用单独的环境，剥离继承的模型配置及名称含 API_KEY、TOKEN、SECRET 等敏感标识的变量，仅添加本地后端代理地址。

后端使用本项目 `data/game.sqlite` 持久化数据，可用服务端环境变量 `SQLITE_PATH` 改到其他位置。能力令牌仅在创建会话响应中返回，不能复制到证据或日志。游戏 AI 区域尚未开放；独立 Provider adapter 的验证不等于游戏 AI 已集成。

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

确认后只删除该指定目录中已知名称的 `game.sqlite`、`game.sqlite-wal`、`game.sqlite-shm`，清除其中的游戏会话与存档。目录必须位于项目 `data/` 内；含其他文件（包括总预算 ledger）的目录、项目外路径、符号链接或目录联接均会拒绝。此入口不会删除或绕过总预算数据。若使用其他数据库位置，请确认其归属并遵守目录限制。

## 当前验证范围与限制

M2 手动范围已通过独立 API（27 tests、0 skip）、浏览器（1280/768/390 完整路线、存档/恢复/重置）和综合 checker（前端构建、27 tests、115 subtests；源码运行期间未变化）。AI 游戏集成与提案、实验、CH01、干净目录交接及真人课程签署仍未完成；不能据此声明项目整体完成或发布通过。没有公开部署或 GitHub Actions。

## 交付材料索引

按六类查看当前材料与未完成项：[`release/README.md`](release/README.md)。M0 基线入口为 [`evidence/index-M0.json`](evidence/index-M0.json)；尚未生成 baseline_v1 正式 manifest。
