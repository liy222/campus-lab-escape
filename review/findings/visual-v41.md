v4.1 独立 QA 已通过并封版，SOURCE STOP。以下准备/基线过程保留为历史；最终结果见文末和 evidence/upgrade/v4.1/qa/result.json。

2026-10-08 操作员 visual_qa_oct08 实际运行 compact API6 方法/3子测试，11.40s，1条既有 Starlette/httpx 弃用警告，exit0；实际 TypeScript/Vite build exit0。两阶段85源文件运行前后都等于 baseline-candidate.json，SHA256 3f803251ed225c147bc59e4be6e9e7d97cff7c4c85919de0a580393e4a90e587，parent1047e293ade70e446c9c76be0a0d751f3e3ad81a。旧12API文件运行前后rawhash一致；原v4.0 wrappers和证据不变，仅机械复制新epoch描述/临时目录prefix/build输出路径，保留相同6方法与断言。

实际命令：C:/Users/liyh/.conda/envs/1/python.exe -B -X utf8 evidence/upgrade/v4.1/qa/baseline-api/runner.py evidence/upgrade/v4.1/baseline-candidate.json →0；同Python参数运行qa/baseline_build.py同候选→0，子命令C:/Program Files/nodejs/npm.cmd run build --prefix frontend→0。封存元数据的qa/seal_baseline.py→0，不执行测试。输出在qa/baseline-api/{runner.py,run.json,stdout.txt,checks.json}、qa/baseline-build/{run.json,stdout.txt}，另baseline-copy.json、baseline-result.json。

完整API127方法/337子测试只复用v4.0历史同backend基线，不重跑、不重复计数。当前只有API/build基线，没有新R2浏览器执行或画面验收。无产品/旧测试编辑、commit、付费模型/真实凭据/真人时长宣称；临时SQLite仅QA所有。基线SOURCE STOP，已通知Main释放R2实施。

R2 新runner静态准备：tests/e2e/run_visual_v41.mjs 从封存v4.0完整路线复制，适配Front提供的公共DOM蓝图：R1/R2实际Canvas输入、独立键盘镜像、module_id/rotation9格、submit_circuit服务确认后独立总闸、CRT表单、托盘真实物体、POWER_ON才显维护签、普通门闩R3与返回R1。新增有意义的错误持有保险丝不推进/统计只加1、六电源态/五终端态、实际总览暗亮像素不同、可读反馈、五个archive（early/slide/partial/powered/win）+legacy的取消/恢复/重置/刷新/进程重启、恢复无progression marker，并保留原R1回归/完整R3灰盒顺序和结算断言。真实hasTouch375新独立session经R1正常取得保险丝，R2触屏搭扣/线路格与键盘护板动作；不直接注入或共享session/archive。

新prepare_visual_runner.py实际仅生成QA文件和Node --check：首次机械替换anchor不唯一退出1，写runner前失败；修复为函数专属anchor后exit0，后续新增case语法检查均exit0，没有服务/浏览器执行。旧13e2e（含v4.0两新脚本）与12API均rawhash保留，见qa/preparation-runner.json。当前runner SHA256 44ee51c6a26889ce011c5b64341442b451b33af0697d65cb7ed394fee6fe3266，静态准备正式运行数0。Front最终SOURCE STOP清单到达后继续只改新adapter，正式R2整条流程须Main固定候选GO。本准备不等于任何R2执行、截图或画面质量结论；QA准备SOURCE STOP。

最终公开选择器静态适配：已读当前Room2Scene/Room2/GameCanvas/bridge/RoomChrome/manifest及相关App/style；实际CRT字段仍是#terminal-username/#terminal-password，标签USER/PASS、提交按钮AUTHENTICATE，故新runner改用字段id与data-scene-action=submit_login、data-target-id=r2_monitor，同时严格断言唯一React表单和两个字段。research_strip/access_card是后端真实对象id，take移除后自动回data-view=room，不要求消失的返回按钮；新增对象移除/背包存在/实际拾取新receipt动画帧断言。维护签overview与电箱近景均用r2_service_label，近景180×96绘制与180×250hitbox共享点击中心，另从电箱近景实际Canvas点标签验证已知线索不重复计隐藏数。Circuit9格用public moduleId/rotation，completed保留disabled，submit与总闸分开。

实际静态命令：同Python执行qa/adapt_live_selectors.py →0，内部node --check tests/e2e/run_visual_v41.mjs →0；没有API/build/Chrome再运行。新epoch为qa/preparation-live-selectors.json，保留原preparation-runner.json历史hash，新runner SHA256 c0307307bc2ea5cae6df87657d387a0c34d37566278dbcb7951e3206ed4275b1，旧13e2e/12API仍全部byte-identical。Frontend最终SOURCE STOP消息确认该协议；其Owner smoke/build只是Owner证据，未冒称QA实际执行。完整旧route/state/stats/archive/auth-baseline/replay断言保留，新R2正式视觉执行仍0，等待Main统一冻结GO。准备SOURCE STOP。

最终正式QA：同一candidate.json SHA256 7ebfaefc93a22a62fd7c002da822f21ab79588641c2dd7609bf3e96d22b18bae，123源全部运行前后及当前匹配；backend/contracts40与R1 SVG26同实际v4.1基线raw字节，旧API12与e2e13字节保留。实际定向API6方法/3子测试、warning1、11.72s、exit0；构建exit0；最终第三轮Chrome339 compact记录、35组真实Canvas非黑非统一像素、21组R2状态/布局记录、issues[]、exit0。没有本阶段完整127API重跑，也不合计基线或前两浏览器重复计数。

实际命令/记录：C:/Users/liyh/.conda/envs/1/python.exe -B -X utf8 evidence/upgrade/v4.1/qa/formal-api/runner.py evidence/upgrade/v4.1/candidate.json →0，证据qa/formal-api/{run.json,stdout.txt,checks.json}；同Python运行qa/formal_build.py同候选→0，实际npm.cmd run build --prefix frontend→0，证据qa/formal-build/{run.json,stdout.txt}；C:/Program Files/nodejs/node.exe tests/e2e/run_visual_v41.mjs同候选三次退出1/1/0，记录分别qa/20261008T010100682Z-browser/run.json（204）、qa/20261008T010350006Z-browser/run.json（278）、qa/20261008T010537916Z-browser/run.json（339，01:05:37.917Z→01:06:23.285Z）。三个都同123源，前两失败属于新QA遗漏刷新/新独立触屏context后的动画observer注册，仅新runner补注册、保留fresh receipt与旧状态断言，产品没有修复/变更。第一错误handler只保存首行，原完整stack无法事后重构，不补造；第二真实stack保留。三个runner epoch归档qa/runner-epochs/，最终runner SHA256 c999fcf488d60793346535b7a4d07b18c7abf31915630923e87d3ae987fc874b。第三轮已启动后Main建议局部复验，随后授权正常收尾；没有第四整条或重复API/build。

已验完整R1回归→R2真实Canvas对象/九格线路/服务端提交→独立总闸→电脑OFF/BOOTING/LOGIN_LOCKED/UNLOCKED/DATA_READ→托盘观察拾取→普通门闩R3→原公共顺序/出口/评分；错误持有保险丝/登录/线路保持核心状态且错误数只加1，候选公开几何线路能接受等价连接。五archive（早期/玻片/线路中期/通电/通关）加legacy槽覆盖指定恢复/取消/reset/reload/真实后端进程restart/新generation，仅快照无动画；统计与UTC结算保留。真实hasTouch375及独立键盘分别验R1和R2维护说明/搭扣/护板/线路格，CRT和托盘另经375普通viewport完整UI与布局检查。旧namespace/light旧槽smoke继续可用。

亲自目视17张实际PNG：第一epoch6张R2暗/亮总览、部分线路、CRT、DATA_READ托盘、维护签；第三epoch手机线路/CRT/托盘、纸条拿取中间帧/稳定帧、R2真实触屏、R1桌面/手机/墙钟、胜利手机长页、五档+旧槽列表。原文/输入可读，暗亮与延迟托盘/维护签可见，四拨盘与21:17修复保留；未发现新的产品问题。图名/hash、执行目录全部artifact hash和123最终source map在qa/result.json。新qa/seal_result.py实际仅封存和hash审计→0，不执行测试；另本review更新。SOURCE STOP交Main验收/文档/Git。

限制：既有Starlette/httpx warning1与Vite>500kB包体warning保留；缺图交互门槛/lazy/Loading/audio/EXIT视觉留4.2，受控missing-asset未验；R3/EXIT仍灰盒，不冒称最终视觉完成。rootCMD未交互启动，实际为自有本机loopback后端进程重启。免费mock/合成临时key UI输入不发送真实provider，paid0；无敏感历史DB、音频质量、真人手动完整路线或真人时长/付费模型质量证据。首轮完整stack截断为真实证据局限。
