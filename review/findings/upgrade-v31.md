# v3.1 独立 QA：通过

最终冻结：`evidence/upgrade/v3.1/candidate-fixed.json`。全套 API 复验 exit **0**，**89 passed（旧82＋新7）、235 subtests passed**，37.82秒；仅现有 TestClient/httpx 弃用警告。13个候选源码哈希 before/after 全部一致。摘要：`evidence/upgrade/v3.1/qa/result.json`。

实际命令：`C:\Users\liyh\.conda\envs\1\python.exe -c <runner>`，runner 调用 `pytest.main(['tests/api','-q'])` 并导出脱敏 HTTP exchanges；完整 executable/argument 数组、exit及源码哈希记录在 `evidence/upgrade/v3.1/qa/formal-api-fixed-20261006/run.json`，同目录 `stdout.txt` 与 `http-exchanges.json` 保存结果。

验收覆盖四条服务器状态链、不同阶段描述/操作/反馈、39步三房间通关、每个设备进阶的 save/reset/restore/Store reopen、严格 interact 参数、auth/replay/stale/generation、污染及跨版本快照拒绝、AI read callback/precheck/confirm 禁止跳步、同一ledger与临时凭据边界。真实网络被禁用，AI只用合成/注入提供器。

首轮全API exit **1**：87 passed／2 failed（旧82全过），证据保留在 `qa/formal-api-20261006/`。其中一项真实[P2]存档缺陷：checksum有效但删掉 `r3_panel` 观察与线索的 `check_done=true` 快照被恢复并覆盖session。Backend Owner修复后，独立复验得到 `409 INVALID_SNAPSHOT`，session与污染slot均未被覆盖，此阻塞已关闭。另一项是新增QA错断言，实际旧契约是 `STALE_GENERATION`；仅修正该期望，未放宽产品断言。修复仅改变 `upgrade_rules.py` 不变量，最终hash `242fe7c7e577018e79bde9ddbc19e68e88325890cc9f1fd641ebfbc226e9ef83`。

修复前独立构建 `npm.cmd run build --prefix frontend` exit **0**，证据 `qa/formal-build-20261006/`。Chrome命令 `node tests/e2e/run_upgrade_v31.mjs evidence/upgrade/v3.1/candidate.json` exit **0**，证据 `qa/20261006T100054304Z-browser/`：实际UI四链／三房间胜利，FUSE_INSTALLED保存恢复、刷新、OS后台服务重启、1280/375px布局、restore/reset/reload清除合成Key，以及同源码legacy入口／level2存档／双storage namespace。截图 `mobile-victory.png` 已目视检查，issues为空。API与Chrome各自 before/after 哈希一致，首轮比较在 `qa/first-freeze-check.json`。

**构建／Chrome属于修复前candidate，不冒称最终源码浏览器验收。** Main明确要求对仅不变量修复复跑全API；正常39步路线及所有设备阶段存档恢复在最终源码再次通过，所以未无条件重复浏览器／构建。

写入：`tests/api/test_upgrade_v31.py`、`tests/e2e/run_upgrade_v31.mjs`、本报告、`evidence/upgrade/v3.1/qa/`；旧 `tests/api/test_m2.py`、`test_ch01.py` 的OS restart环境仅机械增加 `GAMEPLAY_VERSION=legacy`，原断言不变。

无未解决的本版本产品finding。限制：未做真实模型质量／真实玩家时间验收；legacy smoke用QA拥有的公开创建level2 slot，未读取历史敏感DB。零真实付费调用，未读.env/key、未部署、未提交、未重置既有环境。首轮失败和Owner单独修复证据均保留。QA SOURCE STOP。
