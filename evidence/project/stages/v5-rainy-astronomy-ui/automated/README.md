# 本目录的运行记录

- 目录 `browser-<UTC>-<run8>/` 是 `tests/v5/run_visual_ui_browser.mjs` 每一次实际运行的结果，每份包含 `browser-result.json`（run_id、起止时间、源码/构建/素材指纹、逐项 expected/actual、截图清单）。
- 共 19 次运行：14 次 `FAILED`、5 次 `COMPLETED`。最终通过的是 `browser-2026-10-28T16-14-42-322Z-7bd64160`（32 项，exit 0）。
- 所有 21 份 `browser-result.json` 原样保留；**只有最终通过的那一次保留了 PNG 截图**。其余运行的 PNG 在 2026-10-29 提交前删除，原因只是仓库体积（原 99.7 MB），不是重新执行、修改结果或删除失败记录。
- 14 次失败的原因都记录在对应 JSON 的 `execution failure` / 失败检查项里，包括两次真实产品修复（导航控件 38→44px、生成完成后关卡列表延迟刷新）和一次 restore 断言修正。没有把多次运行合并成“单轮全绿”的说法。
- 这些截图都是隔离合成服务（8002 + TEMP 数据库）的自动截图，不是真人截图，也不代表真人接受。
