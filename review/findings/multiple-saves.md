多时刻存档独立 QA：按联合实际覆盖验收，SOURCE STOP。

候选 `evidence/integration/multiple-saves/candidate.json` SHA256 `c4461441e48b0cff9b64421daa3acaa1e29568bf66cba95b157b1a0b49a6d4df`，41产品/契约/规格路径在完整API、定向API、最终build、Chrome及封存时rawhash均一致；原15个API/runner文件字节保持v3.4封存记录一致，未弱化旧断言。仅新增QA tests/runner/report及本任务证据，没有产品修改、付费调用、spawn或commit。

首轮完整API：exit1，**126方法passed、1方法failed；336子测试passed、1子测试failed**，pytest显示2failed，1warning，291.52s。收集范围为118既有+9新方法。两失败都是新QA协议预期：legacy提议因读取存档被invalidate，实际409/PROPOSAL_INVALIDATED；已完成失败request在reset后按新接口receipt-first语义重放409/STALE_STATE。原run/stdout/checks76均保留。只校正新test这两处，补同event_id断言和一个fresh request_id旧generation拒绝检查。

定向原两方法：exit0，**2方法passed、9子测试passed**，1warning，5.19s，compact检查记录31。重复方法/子项/记录不与首轮相加，没有第二次完整127全绿声明。联合结果覆盖同41产品字节，未改产品。

实际命令及退出码：

- `C:/Users/liyh/.conda/envs/1/python.exe -B -X utf8 evidence/integration/multiple-saves/qa/formal-api/runner.py evidence/integration/multiple-saves/candidate.json` →1；内部 `pytest tests/api -q --tb=short -p no:cacheprovider`。
- 同Python参数执行 `qa/formal-api-directed/runner.py` 并传同candidate →0；只执行 `test_additive_archive_routes_preserve_explicit_old_mode_entries`、`test_missing_foreign_auth_bad_fields_stale_requests_do_not_change_archives` 两方法，完整内部参数在run.json。
- 同Python参数执行 `qa/build_check.py` →0；实际子命令 `C:/Program Files/nodejs/npm.cmd run build --prefix frontend` →0，冻结最终前端独立构建。
- `C:/Program Files/nodejs/node.exe tests/e2e/run_multiple_saves.mjs evidence/integration/multiple-saves/candidate.json` →0，实际Google Chrome headless **149checks，issues[]**，各服务启动/重启参数及退出信息在run.json。
- 同Python参数执行 `qa/cleanup_check.py` →0；只读本次精确11自有PID/10端口，均无存活/监听，不杀进程、不影响既有用户服务。

API覆盖immutable多时刻append/list、11字段严格metadata、默认/40字/注入名称、同timestamp/name/revision仍独立、并发与重放只创建一次、operation/save_id/name冲突、不同会话与坏auth、malformed/stale请求、旧单槽schema reopen与原snapshot不重写、corrupt/checksum/owner/version/字段/统计invariant失败不覆盖当前或其他档。早期/partial/won存档恢复完整游戏字段、统计和固定结算，revision+1/newgeneration；受控125秒离线与600秒胜后推进保持结算。所选恢复使旧提议PROPOSAL_INVALIDATED、进行中mock hint STALE_STATE且不增加统计。旧四模式入口保留。

Chrome真实主线创建三个命名档（早期、线路板中期、通关）及旧单槽，玩家按钮选择三时刻、确认/取消、partial旋转与save/restore、reset保留、刷新和实际后端进程重启，继续公开推导两小游戏与胜利；保留三等级提示/可选故事/统计评分、375px及旧namespace smoke。11张截图均亲自目视，其中5张是desktop/mobile存档列表及读取confirm/early面板clip，名称/时刻/房间/读取控件可读；HTML样本是纯文本，不生成img或脚本。该胜利自动路线用时20秒不是人类时长证明。

文件：`tests/api/test_multiple_saves.py` 当前SHA256 `e0a154004431fc8be0098b0277c1cd8a8456edcd7f1a4ff21f968241946f7ff2`；`tests/e2e/run_multiple_saves.mjs` 当前SHA256 `bed78881b88a46b9e26de5dd17a73adacc875b0a682eec4f35b40b53be6d58b5`；QA执行helper、证据及本报告。每阶段hash、完整argv和当前文件hash见 `evidence/integration/multiple-saves/qa/result.json`。

证据：本任务QA目录的 `formal-api/{run.json,stdout.txt,checks.json}`、`formal-api-directed/{run.json,stdout.txt,checks.json}`、`first-result.json`、`harness-correction.json`、`formal-build/{run.json,stdout.txt}`、`20261007T121307604Z-browser/run.json`及11PNG、`formal-browser-stdout.txt`、`visual-check.json`、`cleanup-check.json`。`preparation.json/prepare_check.py`保留历史准备scope/hash，不冒充正式结果。日志仅compact，不导出全状态/session token/key；数据库仅QA临时synthetic。

限制：完整首轮exit1经两方法定向0联合解决，无第二次全量绿声明；existing Starlette/httpx warning未修。未验证真实paid provider质量/Key、真实用户历史DB、交互根CMD启动或人类完成时长；只验灰盒功能/readability，不是最终美术验收。无未解决产品失败。按用户hold停止，不启动Phaser/v4。
