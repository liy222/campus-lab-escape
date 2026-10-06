# 游玩 AI 模式与手动密钥：独立 QA

日期：2026-10-06。Main 明确宣布 Backend `routes.py`/`runtime.py` 与 Frontend 三个源码文件 SOURCE STOP 后执行。此次仅验收新增需求，不重复旧全项目验收，不改变旧证据。

结论：本次新增边界与实际浏览器验收通过，未发现需要 Owner 修复的实现问题。没有真实 DeepSeek 请求、收费调用或真实凭据。真实服务分支为离线合成输入验收，不能当作真实模型回答质量或真实凭据可用性的证据。

## 本任务写入文件

- `tests/api/test_play_ai_settings.py`
- `tests/e2e/run_play_ai_settings.mjs`
- `review/findings/play-ai-settings-20261006.md`
- `evidence/qa/play-ai-settings-20261006/` 下新增验收记录与截图

未修改实现，未提交，未生成子代理，未读取 `.env`。浏览器服务使用独立的 18146 / 15146 loopback 端口和独立临时游戏数据库，结束时停止自身进程并删除已确认位于临时目录的自身临时数据库。没有保留数据库、session token、完整请求 headers、HAR 或原始服务日志。

## 实际命令与结果

工作目录均为 `D:\深度能力`。

| 命令 | 实际退出码 | 结果 / 证据 |
| --- | --- | --- |
| `node --check tests\e2e\run_play_ai_settings.mjs` | 0 | SOURCE STOP 前仅脚本语法准备；不是正式验收 |
| `C:\Users\liyh\.conda\envs\1\python.exe -c "import ast,pathlib; ast.parse(pathlib.Path('tests/api/test_play_ai_settings.py').read_text(encoding='utf-8')); print('Syntax preparation passed; formal QA not run')"` | 0 | SOURCE STOP 前仅语法准备 |
| `C:\Users\liyh\.conda\envs\1\python.exe -m pytest tests\api\test_play_ai_settings.py -q` | 0 | 7 passed，9 subtests passed，1.44s；`api-pytest.txt`、`api-run.json` |
| `node tests\e2e\run_play_ai_settings.mjs gameplay-ai-settings-source-stop-20261006`，首次 | 1 | QA 脚本误以为刷新立即重建 Assistant，实际游戏先显示欢迎页，需要点击“继续当前游戏”；保留 `browser-20261006T064713716Z/run.json`，没有将其归为实现缺陷 |
| 上述浏览器命令，修正脚本后 | 0 | 实际本地 Chrome，375 / 1280；`browser-20261006T064846183Z/run.json`，issues 空 |
| 两张最终截图经 `view_image` 检查 | 成功返回图像 | 手机、桌面模式选择与密码输入布局无可见横向溢出，输入仅显示合成密钥的密码圆点 |

Python 测试有一条依赖警告：Starlette TestClient 当前使用 httpx 的接口被标为 deprecated；不影响上述测试结果。

## 已验证边界

API 的 DeepSeekProvider.complete 被离线拦截；httpx.AsyncClient.send 被禁止。合成 sentinel 不是真实凭据。

- 显式 mock 无需密钥，使用免费模拟，未进入真实适配器或旧注入 provider；没有联网。
- 不带选择 headers 时仍使用已注入的旧 runtime。
- 正常鉴权先于非法配置报错。非法 provider、缺 / 空 key、513 字符 key、控制字符、仅 key 不带 provider、过长 provider、重复 provider / key headers 返回 422 BAD_ARGUMENT；未预留 AI turn，游戏状态不变，响应与 SQLite 中无合成密钥。
- 显式真实分支固定官方 base URL 与 deepseek-flash；request body 保留原有四字段契约。问句误粘当前 key 时，在进入模型消息和 SQLite 之前被隐藏；响应 / trace 也不包含 sentinel。
- 重复 request_id 只产生一次 adapter 调用，返回同一 turn；换 key 后重放已隐藏的同一问句仍不重复调用。
- 两个独立会话同时使用不同合成 key，各自获得独立 provider 实例；旧 app runtime 未被替换，后续无 header 调用仍使用旧注入 provider。
- 适配器超时只调用一次，不自动重试；重复请求也不重试，手动查看物件仍可执行。
- 请求选择使用同一个 canonical budget 路径，两次真实选择之间 budget snapshot 不变，现有账本文件哈希不变；环境中合成的路径 / provider 配置 override 没有创建新预算账本。由于 complete 被拦截，未发生预算预留或结算。

浏览器真实分支在发到 backend 前被拦截，合成响应仅检验 UI，不构成真实 provider 证据。浏览器禁止非 loopback 请求。

- 默认免费模拟；选择真实模式才显示 type=password 密钥输入框，缺 key 时询问按钮禁用。
- 选择、输入、清除密钥和切换模式没有发起 AI 请求；只有点击询问才调用。
- 清除按钮、回到模拟、刷新后继续当前游戏、切换新游戏、重新开始、恢复存档均清空 key；相应上下文变更恢复默认 mock。
- key 不进入 localStorage、sessionStorage 或 cookie；已保存进度与拥有的临时 SQLite / WAL 内容扫描均无 sentinel。
- 真实询问实际浏览器请求带 X-AI-Provider=deepseek 与合成 X-AI-Api-Key；模拟询问不带 key；create/state/save/reset/restore/actions/proposal cancel/confirm 请求都不带 AI headers。
- 请求 body 没有 key，且仍是 request_id、revision、generation、message。
- 收到真实分支的合成回答后切回模拟，历史回答 badge 仍依据该回答 usage；后续实际 mock 回答显示免费模拟。
- mock 建议取消、再询问确认、手动查看物件均正常；本轮不重跑旧完整通关路线。
- 375 与 1280 像素布局检查 document width 和全部可见 Assistant 输入 / 按钮 / 问句控件边界；没有水平溢出。手机与桌面截图已实际目视检查。

## 证据定位

全部证据位于 `evidence/qa/play-ai-settings-20261006/`：

- `api-run.json`、`api-pytest.txt`、`api-source-before.json`、`api-source-after.json`
- 最终 `browser-20261006T064846183Z/run.json`：脱敏请求摘要、实际布局数值、检查列表、实现 before / after SHA256
- 最终四张截图：`mobile-real-missing-key.png`、`mobile-real-synthetic-password.png`、`mobile-mock-proposal-and-manual.png`、`desktop-real-synthetic-password.png`
- 首次浏览器失败 `browser-20261006T064713716Z/` 保留为脚本修正记录

正式 API 与最终浏览器运行中，五个 SOURCE STOP 实现文件的 before / after SHA256 均相同；API JSON 中 source_unchanged=true。没有全项目巨型 manifest。

## 未覆盖限制

未验证真实账户 key、DeepSeek 网络可达性、真实费用或真实模型输出质量；没有批准或进行收费调用。只使用一个本地 Chrome，未重复 Edge / 多浏览器验收。这里只证明新增设置边界和已列出的关键回归通过，不扩展为全项目最终证明。
