# A28 新目录真实AI段只读准备 — STOP

结论：**可复用旧runner的有限流程，但不能在指定clean目录原样直接运行。** 本次只读检查退出0（e6f34c），27文件实际SHA前后不变；选定11份Root/clean代码完全相同且clean原始SHA匹配既有materialization。没有任何新付费请求、.env读取、数据库打开/写入、服务启动、环境/链接创建或Git操作。A28真实AI验收仍未执行。

指定clean：D:\深度能力\data\reproduction\20261005T115741Z\clean。既有记录commit833aafb09ad20dc1ba82cfed198485ce13300067，source archive SHA2979fd06009a9ee27cc13d8e00500b234d8fbf5d5c90a03a9311ed08e163be8a；原报告仅mock、paid0。本次不重跑其安装、build、回归、服务重启或回退。T32/A28要求mock与真实AI分开，新真实段不能替代真人试玩/解释/签署。

## 阻断直接复用的约束

1. tests/real_m3_runner.py的ROOT由脚本路径推导，CANONICAL=(ROOT/data/ai-budget.sqlite).resolve。clean目录该账本不存在；Root现存canonical账本只做exists检查为true，内容/当前余额均未读。
2. 仅让runner指向Root账本仍不够：clean DeepSeekProvider以自身PROJECT_ROOT检查生产路径，Root账本会触发UNAPPROVED_BUDGET_LEDGER。不能用mock transport绕开它，也不能复制账本或让BudgetLedger创建一个clean新额度。
3. scripts/reproduce.py只做mock，清除模型相关凭据并设置AI_PROVIDER=mock；其workspace/output必须是新路径，不能用它在现存clean补做真实段。
4. DeepSeekConfig默认读取模块所在clean/.env并接受三个MODEL_*进程环境值。不得复制Root.env到clean、输出凭据或把凭据放证据。旧runner --main-real-go只是CLI记录标记，任意字符串并非付费授权验证。

## 最少可行后续步骤（本次没有执行）

1. Main先固定clean上述身份及真实段专用证据目录，仅从clean导入backend/contracts/runner；核对指定源SHA。旧runner在clean调用git_read可能取得祖先Root的当前HEAD，不能将其当作clean commit；外部执行记录必须另外固定833aafb...及materialization身份。
2. 若Main明确批准此运行时适配，可在clean/data/ai-budget.sqlite建立**只指向现存Root canonical文件的精确文件symlink**；验证alias.resolve与Root.resolve相同且samefile为true，禁止copy/新账本/新cap。因为runner和Provider均先resolve，二者会继续使用同一Root物理账本，保留现有路径guard。Windows若不能安全建立该链接，应交Owner设计显式可信canonical路径支持；不要通过任意改写guard或注入假transport继续。当前没有建立或试验链接，故该适配仍属待验证准备。
3. 原附件A28真实接入和Root CNY10预算已有用户授权；Main制作具体可审查的单轮载荷/受控续轮模板与限额，再提交具体步骤的自动安全审批，获准后才把凭据私下提供给单独子进程。本次没有调用付费命令，不把旧6/新8评价授权用于A28。固定一个AI turn、最多3 dispatch、单call1000 token/20秒、format_retries=0、额外保守charge<=CNY .50，同时保持Root项目CNY10总额度。旧runner初始检查所有scope的reserved/unknown与frozen；Main应串行安排其他付费段并在实际dispatch前复核共享账本门，避免其他scope并发未知状态。
4. 从clean只运行有限真AI段，使用runner已有TemporaryDirectory中的import-only/game SQLite，与已通过clean/data/runtime/game-v2.sqlite及rollback DB隔离。模型只看新会话公开状态/已发现线索；先真实get_inventory结果，再建议，确认只产生一次进度receipt，重放不新增模型调用。失败立即停止，不自动重试/补结果。
5. 追加实际命令/exit、clean source before/after、模型工具链/usage或NULL、一次确认和重放证据；账本始终是Root canonical，证据不复制DB、凭据或session token。结论限于此受控真AI段，A28真人操作仍单列未完成。

最少新增边界是Main的外部有限执行记录/必要小launcher，以及一个已批准runtime文件路径alias；产品源码、旧runner、schema、旧证据、clean mock结果不需要修改。若要改变强制工具/流程或Provider配置机制，应另派Owner并重新评审，不能把本只读准备当作批准。

## 强制动作与隐藏答案范围

旧runner先由脚本执行两次手动inspect（r1_note、r1_cabinet），不是两个AI进度动作。唯一AI turn的首次tool_choice强制get_inventory；成功工具链通常需第二次模型dispatch收到真实工具结果，最多允许3次。后续tool_choice为auto，但用户消息明确要求提出submit_code值班柜建议，因此不能称模型自主选择完整策略。模型提议不直接推进；脚本confirm一次，再confirm重放。两次confirm也不是两个推进动作。

答案382仅在runner本地proposal断言中；固定用户消息没有382/724/231。R1两个公开inspect使便签和柜门顺序成为已发现线索，模型据此推导属于允许范围。Runtime把验证过的visible_state、过滤的公开history和消息交给build_context，没有把runner期待值或domain private state注入messages。该结论为静态读取，尚未对新clean实际出网payload进行动态捕获；Main后续preview应核这一边界。scripts/reproduce.py的手工标准路线硬编码382/724/231，仅是mock复现路线，不能作为真实模型推理证明。

旧20261002T120735404563Z-m3-real/run.json实际PASS/exit0、2 provider attempts、charge .00804624，绑定旧candidate与当时源码；它证实当时有限链成功，不证明本新目录、当前AI段或自然自主全游戏通过。没有补写旧结论、调查当前费用或推断老师/真人验收。

## 实际文件、命令与证据

仅新增tests/review_a28_real_readiness.py（SHA 6af0b7cb2b79f64cd716f0ad7b5b38c69d9bb2570be6b25c884b2729379060c2）、本报告与evidence/qa/A28-real-readiness-*。实际命令 `& 'C:\Users\liyh\.conda\envs\1\python.exe' -B -X utf8 tests/review_a28_real_readiness.py`，exit0。前面的计划/runner/旧run/reproduce/AI接口/clean身份只读检查均exit0，工具块与安全行为记录在process.json。

readiness.json SHA cef2aadf9d63897200eb7c10bebccb1a885546fb7384061b3fe7c1457a75a1a3；其中source_before/source_after包含27文件，source_pairs保存11组Root/clean/materialized expected原始SHA。旧runner raw SHA401e0dbcebab85c791aa14a86f495bdc0cd18275b63041fbd425d4c87d67689d；scripts/reproduce.py SHA7dc71165e3d42479884f8c821093c6561e98c240766b03e4a0e69454ea9ec0e9。process.json/index.json绑定实际readiness命令、exit和最终文件。最终目录：evidence/qa/A28-real-readiness-20261005T164441803926Z。

未解决项：具体步骤的自动安全审批、canonical alias/配置适配的实际验证、合法凭据注入和有限真AI执行；本次不宣称它们已完成。用户随后要求完成当前小任务后暂时停止，未启动的执行取消。准备完成，稳定STOP。


## Main已准备relay的最终只读快审

只读查看evidence/integration/run_a28_fresh_real.py与A28-real-fresh-request-plan-20261006.json，**没有执行relay**。Main自行发现初版backend/app/ai/tools.py不存在并修正；当前11项均存在且Root/clean原始SHA相同、clean匹配既有materialization（726bf5 exit0）。当前relay SHA 80305b8955f0426d87577d086fd603ed72f2d2d04fddc8ada485095177698a01；request plan SHA 4a2dc205e007de7d690aecf1d9f59c285a4376453cd1772a9369171dc3caed05。清单为real_m3_runner、qa_runner、AI provider/budget/runtime/context、contracts/tools.json、domain/rules.py、scripts/reproduce.py、backend/app/main.py、contracts/api.schema.json，与本只读collector11组范围一致。

真正执行前三条件均保留在可审查代码中，本次只检查逻辑，不连接数据库：

1. 现存Root ledger，cap固定CNY10、frozen0、所有调用已settled（因此pending/unknown0）、总额还能容纳.50；一个AI turn、最多3次dispatch、额外upper .50，无重试。当前余额/状态未由本QA调查或认证。
2. clean模块/文件路径保持115741目录，11项当前SHA匹配冻结materialization；仅创建缺席runtime文件symlink，绝不替换/复制/新预算；strict resolve指向Root现存同一账本；无权限则请求前停止。链接目前仍不存在，故未实测resolve/实际网络执行。原Provider guard未放宽。
3. relay和旧runner均记录source before/after；relay以OUT.exists和exclusive create消费一次执行标记，子进程cwd=CLEAN、-B/-X utf8、无密钥输出；外部candidate833aafb身份独立于祖先Root Git HEAD。正式执行的actualmodule路径、真实sourceafter和限额仍须届时记录，不能从静态快审当作已运行。

快审命令是只读Python文本/AST/hash检查，540d3d、726bf5、55c93e均exit0。中间e7e49d只读检查器临时表达式写成elseFalse导致SyntaxError/exit1，没有导入relay或执行任何行为；修正诊断后726bf5完成11项检查。此处记录真实失败，不作为产品Finding。

用户最新要求当前小任务完成后暂时停止；Main已明确不执行relay。此次只读准备和快审完成，无新模型调用、symlink、环境注入、DB连接/写入、全量回归或费用调查。SOURCE STOP。
