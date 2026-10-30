# V5 临时 API Key 安全检查

日期：2026-10-30。范围只包含现有 `dist-v5` 上的 V5 临时生成 Key 界面；产品源码和既有 KEY-01/02、WEB-01/02 结果未改写或重跑。

## 实际结果

最终集中运行：`node tests/v5/run_key_safety_browser.mjs`，退出码 **0**，10条记录全部通过。完整脱敏结果在 [最终结果](../automated/browser-2026-10-30T13-40-45-503Z-67fd5aac/result.json)，逐项记录在同目录 `records.jsonl`。最终运行对应 HEAD `d6806b17a1e779b68d6b5dbc9a155e513ae9cd6b`，实际加载 `dist-v5` 脚本 `index-nlwtZpdA.js`。

| 范围 | 实际结果 |
|---|---|
| 空 Key | 生成按钮可用；空值提交后没有生成 POST。 |
| 失败提交 | runner 在本机路由层注入固定 Synthetic 503；Key 清空，页面错误提示未包含 Canary。此项不是后端失败行为验证。 |
| 刷新、退出、换号 | 填入 Canary 后刷新清空；退出并登录不恢复；另一标签通过真实退出与登录 UI 切换至第二个 Synthetic 账号后，原标签 Key 为空。 |
| 成功提交 | 隔离 Synthetic API 返回 202 后 Key 清空。该异步生成只证明本次提交与清理，不等待关卡进入 ready。 |
| Canary 传输 | 两次带 Canary 的生成请求中，值只出现在发往本机生成接口的 `X-AI-Api-Key`；URL、请求正文、其他请求头、V5 API 响应正文、localStorage、sessionStorage 命中均为 0。输入仍含 Canary、提交前即检查存储；随后等待完毕的42个 API 响应扫描，未读响应数为0。结果只记录 Canary ID、计数和布尔值。 |
| 外部/真实调用 | 外部请求 0、真实模型调用 0、付费调用 0；自有 8002 fixture 已停止。 |

空 Key/失败后截图：[失败后清空](../automated/browser-2026-10-30T13-40-45-503Z-67fd5aac/after-failure-key-cleared.png)；成功受理后截图：[成功后清空](../automated/browser-2026-10-30T13-40-45-503Z-67fd5aac/after-success-key-cleared.png)。截图均来自 1280×720 Synthetic UI，拍摄时输入框为空。

## 命令与保留的失败

- `node --check tests/v5/run_key_safety_browser.mjs`：退出码 0（runner 语法检查）。
- `node tests/v5/run_key_safety_browser.mjs`：最终退出码 0，上述结果目录。
- 初始运行在主题选择器定位失败，退出码 1：[13:31 结果](../automated/browser-2026-10-30T13-31-48-965Z-25c1fa2c/result.json)。
- 修正主题定位后，空 Key 点击定位失败，退出码 1：[13:32 结果](../automated/browser-2026-10-30T13-32-59-080Z-4cf58738/result.json)。
- 增加阶段诊断后仍在空 Key 按钮点击超时，退出码 1：[13:34 结果](../automated/browser-2026-10-30T13-34-10-448Z-29c55dbb/result.json)。
- 使用界面实际按钮并等待其启用后，空 Key 检查通过，生成返回 202；该轮因等待完整关卡进入“开始探索”而超时，退出码 1：[13:35 结果](../automated/browser-2026-10-30T13-35-32-555Z-30d122e1/result.json)。此等待超出本阶段 Key 生命周期范围；该响应事实保留，未将该轮称为通过。

最终报告前，Main 对 runner 复核发现异步响应扫描没有等待、跨页失败分支可能手工登录掩盖广播问题、存储只在最终检查等三个测试侧缺口。QA仅修新runner：等待响应扫描并计数、要求第一标签自行收到第二标签真实 UI 换号状态、增加提交前存储观察；同时记录 Git HEAD 和实际加载脚本名。随后只重跑本阶段同一范围。此次调整是测试检查器收紧，不是产品回归或产品变更；上述失败原件均保留。

最终范围使用本地固定 503 覆盖失败分支，并以成功请求的 202 与输入清空作为终点，避免把 Synthetic 生成关卡的后续 ready/通关作为 Key 检查条件。

## 限制

测试在本机隔离后端、Synthetic 用户和现有 `dist-v5` 上执行；失败分支由 Playwright 本地路由模拟。它验证浏览器端输入状态、页面请求边界和本地存储，不验证操作系统内存、浏览器扩展、真实 DeepSeek 服务或真实 Key。没有重建前端，也没有重复用户名、密码、账号隔离及既有后端套件。
