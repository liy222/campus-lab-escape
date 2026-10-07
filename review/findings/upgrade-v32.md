# v3.2 独立 QA：修复复验通过，SOURCE STOP

冻结候选 `evidence/upgrade/v3.2/candidate-fixed.json` 的23源码，完整API复验前后与候选完全匹配；全部API测试文件也前后匹配。新旧候选仅 `backend/app/ai/runtime.py` SHA256不同。最终摘要 `evidence/upgrade/v3.2/qa/result.json`，首轮失败 `first-result.json` 与原始运行证据全部保留。

实际命令 `C:/Users/liyh/.conda/envs/1/python.exe -B -X utf8 evidence/upgrade/v3.2/qa/formal-api-fixed-20261007/runner.py`，入口调用 `pytest.main(['tests/api','-q','-p','no:cacheprovider'])`，exit **0**：**97 passed、257 passed subtests、1 warning**，51.16s；旧89测试及新8方法均通过。命令参数数组、真实exit、起止时间、23源码与测试文件SHA256：`qa/formal-api-fixed-20261007/run.json`；脱敏stdout与221条精简阶段／拒绝记录在同目录 `stdout.txt`、`checks.json`，未导出全state或session token。环境为mock、legacy导入入口及QA独占临时SQLite，各fixture独立数据。

首轮[P2] `existing-clue-future-fact` 已由独立完整API复验关闭：inspect当前门的合成callback不能替换既有线索完整record，Runtime在第二次provider调用前stopped，sentinel未进入provider上下文，Store不变。现有12种伪造读取子例全部拒绝，包括重复既有clue ID；合法中性inspect/get_inventory和安装玻片后发现42正常。Owner定向3/11证据属于修复自验；本次正式完整集包含后来增补的重复ID子例，计数按实际结果记录。

新版测试覆盖公开线索独立推导4217、LAB-42/2117、4792；空背包／未供电未登录提前探索R3；4物品正确与错误目标；46步完整路线；各设备／槽／终检阶段save/reset/restore/reopen；strict登录及错误尝试无副作用；污染／跨版本快照拒绝且不覆盖session/slot；AI precheck/confirm/receipt replay/generation及读取知识边界。旧legacy/v3.1回归保留，版本数据隔离；没有读取历史敏感数据库。

复用原候选已封存的构建与浏览器结果，未重复运行：`npm.cmd run build --prefix frontend` exit **0**，`qa/formal-build-20261006/`；实际Chrome命令 `node tests/e2e/run_upgrade_v32.mjs evidence/upgrade/v3.2/candidate.json` exit **0**，61摘要检查、issues空，`qa/20261006T103711980Z-browser/`。原浏览器before/after23源码均匹配原候选；真实点击3房间灰盒／提前探索／胜利、保存恢复刷新、OS后台服务重启、375px布局、登录字段清空、legacy/v3.1轻量slot/storage隔离。四张截图的目视检查为首轮既有证据，本轮没有重复检查或声称新截图。

启动CMD原字节／配置检查exit **0**，无CRCRLF/BOM，全部CRLF，选择upgrade＋game-v3.2 DB＋mock；`qa/launcher-byte-check.json`。**没有实际启动根CMD**。

本复验仅新增 `qa/formal-api-fixed-20261007/{runner.py,run.json,stdout.txt,checks.json}`、最终 `qa/result.json`，更新本报告；未修改产品或测试断言。旧QA测试/runner的v3.1 selector归属准备期，`qa/preparation.json`原证据保留。首次读取曾误用不存在的 `tests/test_upgrade_v32.py`，读取命令exit1，随后读取实际 `tests/api/test_upgrade_v32.py` exit0；未影响正式测试。

零付费调用，无真实模型网络、.env/key/历史敏感DB读取，无部署/提交。限制：合成callback/providers及mock只能确认规则和边界，不能证明真实模型提示质量；没有真实玩家20–30分钟通关用时验收；runtime窄修复后未重跑构建/浏览器，复验适用范围按上述证据记录；现有Starlette TestClient/httpx弃用警告仍在。QA SOURCE STOP，等待下一版本任务。
