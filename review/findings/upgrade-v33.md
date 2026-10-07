# v3.3 独立 QA：联合证据验收通过，SOURCE STOP

冻结 `evidence/upgrade/v3.3/candidate.json` 的27产品/契约/规格/launcher文件，首轮API、定向API、构建和Chrome各自before/after及最终hash均匹配。最终 `evidence/upgrade/v3.3/qa/result.json`；首轮 `qa/first-result.json`。没有改产品，也没有一次完整106passed/exit0的声明。

完整API实际命令 `C:/Users/liyh/.conda/envs/1/python.exe -B -X utf8 evidence/upgrade/v3.3/qa/formal-api-20261007/runner.py`，内部 `pytest.main(['tests/api','-q','-p','no:cacheprovider'])`，exit **1**：**105 passed、1 failed、291 passed subtests、1 warning**，69.04s。旧97项全部通过，新9方法中8通过。唯一失败为QA尾部错误假设：泛用 `interact r3_panel` 期待200，但公开动作与设备正确返回409 PRECONDITION_FAILED阻断旁路。此前旧numeric/电箱generic/伪solved/冻结/四次旋转no-op检查已通过。原run.json/checks.json原样保留；导出stdout-compact保留测试trace、scalar失败及完整统计，未导出全state。

Main允许仅修新QA预期并定向复验。`tests/api/test_upgrade_v33.py` 尾部改为reject(PRECONDITION_FAILED)并验证完整visible_state不变，增加严格性；无旧断言弱化。实际命令 `C:/Users/liyh/.conda/envs/1/python.exe -B -X utf8 evidence/upgrade/v3.3/qa/formal-api-directed-20261007/runner.py`，精确指向上述失败方法，exit **0**：**1 passed、3 passed subtests、1 warning**，2.46s。同27冻结产品hash；仅QA方法单处变化的前后hash、归因和本地raw路径在 `qa/harness-correction.json`。因此以首次完整已过97+8与定向已过第9方法联合验收，**没有重复整套API**，子测试数字没有相加冒充唯一用例数。

不可提交的首次公开state失败diff保留本地副本：`C:\Users\liyh\AppData\Local\Temp\campus-v33-qa-raw-64_0pcrr\first-api-stdout.local.txt`，SHA256 `c4d1bf01ede17a684584fbd2ccbab71eb1945f98d2bb3ece274bc0ab3500898b`。该本地文件未删除、含token字段已由fixture脱敏，无API key；不提交或导出它。原stdout仅移出repo，compact副本显式标注省略全state，实际exit/trace/命令/hash/统计保留。

9个新版API方法实际覆盖公开 I/L 端口搜索source→sink互惠路径、I180°等效合法连通（不读取Backend私有期望数组）、R1源符号/R2位置/R3设备legend独立推导顺序；partial/completed线路及终检save/reset/restore/reopen与胜利；未知/未露出/非当前房间盘为空；客户端伪solved/no-op/genericinteract/旧numeric不推进；strict module/角度额外字段/未知设备/四项长度/重复；新request冻结拒绝与旧receipt replay；跨版本快照不改session/slot；AI schema-valid旧未知盤注入、旋转/完成状态/设备mutation拒绝及合法读取保留partial board；manual-only新动作未加入provider tools。

实际 `C:/Program Files/nodejs/npm.cmd run build --prefix frontend` exit **0**，`qa/formal-build-20261007/{run.json,stdout.txt}`。实际 `C:/Program Files/nodejs/node.exe tests/e2e/run_upgrade_v33.mjs evidence/upgrade/v3.3/candidate.json` exit **0**，**102摘要检查、issues空**，`qa/20261007T060045594Z-browser/run.json` 与 `qa/formal-browser-console-20261007.txt`。Chrome真实模块旋转和explicit submit替代合法电路；partial save/reset/restore/reload、OS backend restart后原盘；总闸后登录；跨房间设备顺序；错序409/重复422不改进度，错序草稿四项保持；restore/reload/房间切换清空；完成状态存档恢复、终检释放/推门/移动EXIT胜利；375px线路/顺序/登录/各房间/胜利无横向溢出；legacy/v3.1/v3.2轻量新建slot及session namespace隔离。没有以API直接调用代替小游戏UI。六截图已目视检查，`qa/visual-check.json`；线路与顺序截图为桌面，mobile胜利有截图，375px盘另由实际DOM几何检查验收。构建/浏览器均未重复。

启动器首次检查exit **1**是QA字符串假设错误（期待不存在的--mock/--gameplay-version）。按实际 `set GAMEPLAY_VERSION=upgrade`、`set SQLITE_PATH=./data/game-v3.3.sqlite`、`-m scripts.dev --provider mock --open-browser` 定向检查exit **0**，无CRCRLF/BOM、全CRLF、文件hash匹配、dev保留旧模式，`qa/launcher-byte-check.json`；首次 `qa/launcher-byte-first.json` 保留。**没有实际启动根CMD**。

准备与收尾raw-byte只读核对：旧v3.2/v3.1 fixture+runner共4文件与519c8d0 byte-identical，已显式版本，无selector或断言改动。`qa/preparation.json` 首次static ownership失败及限定单命令safe.directory后exit0仍保留。浏览器首跑前仅QA错误摘要privacy调整，`qa/browser-preflight-privacy.json`，不改actions/断言。

文件：新 `tests/api/test_upgrade_v33.py`、`tests/e2e/run_upgrade_v33.mjs`；本报告；`evidence/upgrade/v3.3/qa/`准备、first/final/修正/visual/launcher与两API/构建/Chrome证据。实际命令数组、真实exit、stdout、before/afterhash按各run.json保存，简化阶段共首轮212及定向39条（重叠，不当作独立用例）。零付费/真实模型网络/.env/key/历史敏感DB读取，无部署/spawn/提交。无未解决产品失败；限制是联合API证据而非第二次full绿色、rootCMD未启动、现有TestClient/httpx warning、没有真实模型质量与真人用时结论。QA SOURCE STOP。
