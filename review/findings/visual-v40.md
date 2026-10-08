v4.0独立联合QA已封版：首次完整功能范围与修后三项窄复验共同通过，SOURCE STOP。以下原准备与首轮过程保留为历史记录；2026-10-08恢复收尾结论见文末及qa/result.json。

已完整阅读唯一视觉计划docs/visual-plan.md（2227行，SHA256 488d14ee490ba43bbb91186001ba7847fbf153554a235ae0a2ce7ae35944929e）、现有App/Assistant/API/main/package/style及相关旧测试/helpers/多存档Chrome流程。按4.0只R1、4.1R2、4.2R3/polish顺序；不改当前server规则/状态/AI/统计或多存档。计划的历史v3.4基线不回滚最新多存档工作。

实际基线：127方法passed、337子测试passed，1existingwarning，274.87s，API exit0；独立frontend TypeScript/Vite build exit0。两阶段41source before/after均匹配baseline-candidate；API阶段test文件before/after字节一致。候选SHA256 7f653d1a7a675a713c0a1643d96348ba2d1542f27cdcd5dada004733b0ed55f3，HEAD9762fae。没有旧测试/产品改动、付费调用或旧证据覆写。

命令：

- C:/Users/liyh/.conda/envs/1/python.exe -B -X utf8 evidence/upgrade/v4.0/qa/baseline-api/runner.py evidence/upgrade/v4.0/baseline-candidate.json →0；内部pytest tests/api -q --tb=short -p no:cacheprovider（mock/legacy import、owned temporary SQLite）。
- 同Python参数执行evidence/upgrade/v4.0/qa/baseline_build.py →0；实际子命令C:/Program Files/nodejs/npm.cmd run build --prefix frontend →0。

文件/证据：qa/baseline-result.json、baseline-api/{runner.py,run.json,stdout.txt,checks.json}（78compact记录）、baseline_build.py及baseline-build/{run.json,stdout.txt}。完整argv与41rawhash在run.json，原历史记录未动，不导出session token/key/fullstate。

静态准备已完成：新tests/e2e/run_visual_v40.mjs保留旧多存档runner的完整三房间路线及状态断言，新增1920/375场景、真实Canvas命中与独立键盘、R1近景、错误玻片组合/锁码只增统计、笔记每页最多两条原文、AI抽屉本地开合且合成输入不发送、四个存档时刻及旧槽、R1刷新/后端重启、恢复只snapshot与receipt动画标记。旧runner不改字节，12旧API文件与基线一致；其余旧e2e原始hash列于qa/preparation-runner.json，供正式阶段前后比对。

实际静态命令：同Python参数执行qa/prepare_visual_runner.py →0（只生成新QA文件），qa/seal_preparation.py →0；实际Node子命令C:/Program Files/nodejs/node.exe --check tests/e2e/run_visual_v40.mjs →0。两个新正式API/build wrappers仅AST解析准备，不执行服务或测试。API准备选择既有6个有意义的方法覆盖三级提示/错误统计/隐藏与评分/UTC离线/多档/恢复pending hint；复用初始全API基线须绑定Main冻结的同一backend/contracts源码，不声称视觉阶段另一次完整127全绿。所有准备记录在qa/preparation.json及preparation-runner.json，无占位执行命令。

准备SOURCE STOP。渲染准备新epoch见qa/preparation-runner-renderer.json，保留原preparation-runner.json；不限定WebGL，明确Canvas/WebGL均需assets-ready加实际Canvas PNG的非黑/非统一像素检验，并保存截图供目视。像素检测器只以自有synthetic black/uniform-dark/varied-visible PNG验证，详见qa/pixel-fixtures.json，不冒充游戏截图。最终selector与candidate仍待Frontend SOURCE STOP/Main GO；formalvisualruns0，没有新游戏画面截图或真人验收宣称。已准备12组cases，受控missing-asset专例尚未加入runner，正常加载、场景复建、单Canvas和浏览器异常检查已纳入。

正式第一候选candidate.json SHA664b3474a5429d65ee455845d794df20d5aec741d9f7c4a67e09dee5e7088fb8（85source）：targeted API6方法/3子项passed、1existingwarning、12.95s、exit0；final build exit0；第三次Chrome完整范围206 compact记录、10组实际Canvas非黑非统一检验、issues[]、exit0。6方法并非重新全量127，复用全API基线事实单列；各已过阶段85source before/after均匹配同候选。

实际命令：同Python执行qa/formal-api/runner.py evidence/upgrade/v4.0/candidate.json →0；qa/formal_build.py 同候选 →0（npm run build --prefix frontend）；C:/Program Files/nodejs/node.exe tests/e2e/run_visual_v40.mjs 同候选，第一次/第二次/第三次分别exit1/1/0。前两次为新QA结构适配错误（菜单统计容器、generation恢复后菜单关闭），35/45记录及rawhash验证的runner三epoch留qa/browser-attempts.json与runner-epochs/；仅新adapter修正，exact3/row可见原断言保留，不累加重复计数或声称一次全绿。

真实Chrome完成R1Canvas鼠标/独立键盘与hasTouch375 touchscreen.tap、三级免费提示及real选项合成输入开合记忆（未发送）、四archives+旧槽的选读/取消/统计恢复、刷新/实际后端进程重启、R2/R3灰盒完整小游戏主线、胜利冻结及旧namespace轻量smoke。12旧API与11旧e2e字节保持，source/test/no-paid证据在qa/first-result.json与各run。

独立目视19图：R1桌面/手机/触屏画面可见且无长期热点框，柜锁接受仍闭/明确开柜、拾取前→飞入背包中间帧→物件移除稳定帧可区分。发现并通知Main：V40-READING桌面反馈条遮住clock/目镜LAB SAMPLE42/记录/相片原文；V40-CLOCK时针向左下不符合21:17的278.5°左上；V40-LOCK锁特写只有3拨盘，计划574要求4位。qa/first-result.json保留实际图hash与pending三项，不以data marker或非黑像素冒充视觉质量。Main安排窄修，qa/prepare_visual_fix.py只生成新run_visual_v40_fix.mjs（语法exit0）；增量复验与build等待新candidate-fixed冻结GO，不重复已过API/全route。

限制：现有Starlette/httpx弃用warning不作本阶段改动。R1为原创SVG风格，R2/R3仍灰盒，不冒充后续房间美术验收；未测受控missing-asset失败/音频质量、未互动启动rootCMD；无真实模型/真实历史DB/真人试玩或真实完成时间宣称。当前是功能联合覆盖加三项实际视觉finding，最终结论待固定候选窄复验。

2026-10-08 独立恢复收尾：visual_qa_oct08 只读核对现有执行证据，并亲自目视修后6张关键PNG；没有执行此前127方法、6方法、206或112条浏览器记录，没有重跑任何正式测试，也不推断历史QA的实际运行模型。固定candidate-fixed.json SHA256 524ab24a54f39405430f2a53446dc221702aa671e090e2858cda3ee02e63a9e3，85源文件仍匹配。initial→fixed仅style.css、r1_clock.svg、closeup_clock.svg、closeup_cabinet_locked.svg变动，其余81路径相同；backend/contracts内容未改，旧12API/11e2e字节一致。

真实修后记录：qa/20261007T140546920Z-browser-fix/run.json，2026-10-07T14:05:46.921Z→14:06:02.952Z，C:/Program Files/nodejs/node.exe tests/e2e/run_visual_v40_fix.mjs evidence/upgrade/v4.0/candidate-fixed.json →0，112条记录、issues[]；26组反馈/原文/控件矩形检查，31组真实Canvas像素检查，1920/1280/375宽度覆盖clock/record/plaque/eyepiece/four-wheel-lock/wrong-code/photo/restored-photo，另验柜锁接受仍闭、开柜、拿保险丝、R1旧槽save/reset/restore仅快照。SVG几何子命令python -B -X utf8 evidence/upgrade/v4.0/qa/svg_check.py →0，时针278.5°、分针102.724°/102.002°、4拨盘。修后build记录qa/fixed-build/run.json：npm.cmd run build --prefix frontend →0，85源before/after均匹配同固定候选。

目视并关闭V40-READING/V40-CLOCK/V40-LOCK：fixed-clock-reading-1920.png、fixed-eyepiece-reading-1920.png、fixed-four-wheel-lock-1920.png、fixed-clock-reading-375.png、fixed-wrong-code-375.png、fixed-restored-photo-reading-375.png。反馈移到页面顶部，不遮线索/返回/输入；墙钟时针左上与21:17一致；四拨盘可见；375px的原文、错误反馈、输入和恢复相片均能阅读。各图rawhash在qa/result.json。其余初始19图的历史目视记录仍只归原QA，不冒称本恢复操作员亲自看过。

联合复用边界：previsual完整API127方法/337子测试0 + initial稳定候选targeted6方法/3子项0、build0、Chrome2060 + fixed四路径build0/窄Chrome1120。重复计数不相加，未产生第二次完整127全绿或修后全三房间路线宣称。初始Chrome覆盖实际hasTouch/keyboard、四archives及旧槽、selected restore/cancel/reset、刷新/后端进程重启、R2/R3灰盒到胜利及旧namespace轻量验证；修后375宽度为普通viewport，真实触屏归初始epoch。

最终文件：新evidence/upgrade/v4.0/qa/seal_recovery.py、qa/result.json；更新本review报告。seal_recovery.py实际运行exit1、exit1、exit0：前两次仅新收尾校验器误设基线manifest包含40全部路径，以及GitLF/工作区CRLF原字节相等要求，均在生成result前失败、不是产品/正式测试失败。修正为31个基线实际manifest文件rawhash一致，加40个Git基线内容比较，其中36个Git原字节相同、4个只存在既有LF/CRLF差异；保留85个运行manifest全字节相等要求。该过程与准确路径在result.json，不改产品、旧测试或历史证据。最终命令C:/Users/liyh/.conda/envs/1/python.exe -B -X utf8 evidence/upgrade/v4.0/qa/seal_recovery.py →0；内部40次git show 9762fae018d39beea07c58207d2715227b537d00:<backend/contracts路径>各0，仅只读；未commit。

未决限制仍保留：existingwarning1，R2/R3仍灰盒、受控missing-asset未验、rootCMD未交互启动、无音频质量/真人手动完整路线/真实完成时间/付费模型质量/敏感历史DB证据。既有自动化完整路线可证功能覆盖，不能等同真人体验验收。最终QA SOURCE STOP，v4.1准备与正式执行须等待Main的后续GO和新稳定冻结候选。
