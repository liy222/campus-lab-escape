# 2026-10-28 体验反馈集中复核

独立 AI QA 在本次有限 Synthetic 范围内通过，未发现阻断问题。无真人验收或真实模型主题质量结论。

- 定向 API：主题输入/原回复保留与费用边界、主题脱敏/账号隔离、旧完整定义存档恢复，共 5 passed；768314，pytest exit 0，5.85 秒，1 条警告。精确命令见 `evidence/upgrade/v5.0/experience-20261028/api-result.json`。
- 浏览器：使用已有 dist-v5，独立新 context 将全部 8001 请求转发到自有 8002 TEMP 服务，保持原 Host/Origin；未接触用户 8001 预览、账户或数据库。Synthetic 注入与公开文案已明确标注。
- 实际旋转 3×3 线路并提交成功后，九模块与提交按钮均 disabled，cursor 非 wait；错误线路反馈后恢复可操作；延迟真实动作请求期间 aria-busy 为 true。1280×720、390×844、812×375 关键面板可滚动，可用控件至少 44px，无横向溢出。
- 主题在关卡列表、游戏档案和重登后保留，故事展示正确；实际新建存档、推进、选择恢复一次通过。旧无 theme 情况采用明确的响应字段省略模拟，故事回退正常。

首浏览器 `node tests/v5/run_experience_browser.mjs`（29e57a/fb0bc2，exit 1）在生成前因 QA select 标签 exact 匹配超时；原创建页截图和结果保留。修正定位后 `--remaining`（8ae86a/825798，exit 1）完成线路、布局、存档范围，最后因 QA 未从注册表单切回登录而超时；`--tail`（fccbca/c95c82，exit 0）只复用同一自有 TEMP 账户补重登和旧字段模拟。已成功 API、线路、布局与存档未重复，不称单次全绿。自有服务均已停止。

必要截图位于 `evidence/upgrade/v5.0/experience-20261028/`：创建页及 `browser-run2/` 的桌面游戏、三视口线路板、手机游戏。QA 实际查看创建页、桌面游戏及手机线路板；Main 另以 AI 角色查看创建页、桌面线路板及手机游戏，未见可见错位/布局阻断。

复用 Frontend Owner 唯一成功构建，未重建；无付费、Key/账本/玩家库访问或真实原稿记录。通用校园素材限制在界面可见；Synthetic 文案展示不证明任意真实主题遵循，视口检查也不代替物理设备或真人体验。仅完成本次反馈范围，未跑完整路线或旧全套。

文件：`tests/v5/experience_fixture_server.py`、`tests/v5/run_experience_browser.mjs`、本报告及本轮结果/必要截图。SOURCE STOP。
