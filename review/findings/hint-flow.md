# 默认提示流程修正：独立 QA

结论：冻结候选 `cae6d5cb1b42e1a5ad036b973f3ffaa19bd933ee15655c3bfe1e80b2ec3b3ac7` 在本轮约定的定向范围通过，无未关闭产品发现。实际执行者为独立 QA；不把 Owner 开发验证计入正式结果。

实际命令（工作目录 `D:\深度能力`，均显式提权启动本机隔离 helper）：

- `C:\Users\liyh\.conda\envs\1\python.exe -B -X utf8 tests/hint-flow/run_api.py evidence/integration/hint-flow/candidate.json`，exit 0；首次正式 API/领域执行 11 methods，12.371 秒，0 failures / 0 errors。新 7 methods 与未修改的旧 4 methods；不宣称旧全套通过，不另报未单独统计的 subtests 数。
- `C:\Program Files\nodejs\node.exe tests/hint-flow/run_browser.mjs evidence/integration/hint-flow/candidate.json`，exit 0；一次 TypeScript 检查 exit 0、一次 Vite 生产构建 exit 0、桌面 Chrome 记录 71 条（含前置 API 和进程清理，不能称 71 个独立断言），issues `[]`。
- 准备期仅 Python AST 解析 3 文件与 Node `--check`，exit 0；不算产品测试。没有失败正式 epoch、重复构建或重复 API 套件。

接口证据：`evidence/integration/hint-flow/qa/20261018T052105812289Z-api/`。从合法真实领域路线重建 116 个投影记录（主线、提前跨房及跳过推理线索但猜中解法的分支，包含重复状态；不是 116 个唯一状态），逐候选三级渲染、已知 refs 子集与 refs 唯一性检查均通过。原 6 主题共 18 文本逐字保持。人工结合公开 objects、observed、inventory、device_states 审阅新增 L3 指引：取/放/重看玻片、开柜、拿保险丝、开盖/移护板/安装、线路完成后的合闸、两次启动/登录后读记录、托盘收取、插纸/刷卡/启动、终检后的释放/推门/离开，均对应当前阶段，没有把后台完整答案当作提示。

临时 SQLite HTTP 实测覆盖初始观察提示、有效新请求每次 +1、同请求重放不加、同资格集合默认轮换、强度生效、过期 revision/generation、合成 provider 失败/超时、并发重复、进行中的手动操作与恢复冲突。无可选主题的已通关状态使用准确回退且不计数。Store 对伪造 prose 重新渲染；未知 refs、proposal、stale、stopped 内容不能注入结果；read_tool 被禁止，提示未改变已观察对象、物件、设备或主线进度。命名存档恢复和 Store 重开保留强度、计数及据此恢复的轮换位置。

UI 证据：`evidence/integration/hint-flow/qa/20261018T052128899Z-browser/`。仅 1280×900 桌面；实际默认无问题 label/textarea/字数或 key，可直接获取免费提示；三级输出不同；两个原主题轮换。切换真实模式保留问题框及 key/格式检查，切换与输入不发 AI 请求，未点击真实请求。实际命名存档、刷新继续、选定读取恢复计数/强度/下一轮主题；R3 提示没有提交终检。另以隔离 legacy 后端与 Vite 开发视图实际验证旧输入及免费 mock 提交；没有第二次生产构建。人工查看全部 5 张实际截图，默认/真实输入/恢复/R3/旧版符合各自范围。

旧测试政策：68 份原测试文件原始哈希保持。`test_initial_fixed_statistics_no_future_boards_and_no_hint_paid_request` 的初始 NO_HINT/no-count 断言已被本次需求取代；旧 `test_three_levels_only_known_context_no_auto_inspect_no_private_full_solution` 的固定首主题 refs 预期也不用于本轮接受。两者原文保留，新测试覆盖新增规则。实际复用的 4 个旧 method 名称和排除原因记录在 preparation.json；没有弱化断言或宣称全套旧测试通过。

文件：新增 `tests/api/test_hint_flow.py`、`tests/hint-flow/{prepare.py,run_api.py,run_browser.mjs,seal.py}`、本报告以及新 `evidence/integration/hint-flow/qa/`。未修改产品、旧测试或旧证据，未提交。

限制：这是约定的提示定向 QA，不是整个视觉/后端全套验收；没有手机测试、历史用户数据库、真人体验时间、真实 provider 质量或付费调用。保留既有 Starlette/httpx 弃用与构建大包 warning，不影响实际 exit 0。没有主张真实 AI 新增自由问答功能。
