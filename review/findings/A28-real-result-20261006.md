# A28 新目录真实AI段独立验收 — 有限PASS，SOURCE STOP

Main有限真实段实际exit0（6c6318），独立QA实际exit0（e56e64）：105项检查无失败，85个逐文件读取SHA前后不变。**只认证受控R1单轮真实工具链、提议/确认/重放与来源/预算边界；不认证自然自主全游戏、真人试玩或教师批准。**

Main实际外层命令：`C:\Users\liyh\.conda\envs\1\python.exe -B -X utf8 evidence/integration/run_a28_junction_real.py`，exit0。真实子进程使用同Python、-B/-X utf8、-m tests.real_m3_runner，cwd为data/reproduction/A28-junction-20261006/clean。run开始UTC2026-10-06T04:32:35.869965+00:00，结束04:32:39.299774；statusPASS、2次付费、1个AI turn、记录额外conservative upper .0060632 CNY（<=.50），不是供应商账单。

## 身份、原账本与真实链

Candidate833aafb09ad20dc1ba82cfed198485ce13300067；新workspace同833 source archive SHA2979fd06009a9ee27cc13d8e00500b234d8fbf5d5c90a03a9311ed08e163be8a/pins SHA7e7013be5d40d7639f2e2d48fefacf2d24c8f7ebdf4e1a6aec3dd3b5f9b29977。Main材料化10778文件的actualexit0 c986b6归准备记录，本QA仅按要求核11目标文件，不重复10778或全量安装/build/mock回归。已通过的115741完整mock检查仍是另一记录，未迁移/覆写或冒充新执行。

新relay SHA4f6f0aa4fdbc2b3be2b83fa4428cc44eaef738eaf2de796b2d262e19513e05a7。准备和执行均确认Junction的alias.resolve(strict=True)指向D:\深度能力\data\ai-budget.sqlite；QA再次只用metadata验证samefile=true，未复制账本、建立新预算或放宽原Provider path guard。前后保存快照canonical路径相同、cap=CNY10、未冻结；新增恰2个game/settled、有已知usage的call ID，分别与两个server trace provider_result一致。QA未打开实时DB、读取余额或调查费用，只检查保存快照与有限段上限；此证据不代表随后当前余额。

run实际63项source before/after相同，QA逐读当前clean63项全匹配；relay11项before/after/currentRoot/clean也一致。完整current maps在result.json。-m启动的cwd为clean，relay移除PYTHONPATH/PYTHONHOME，源码收集器路径来自该clean；这支持来源绑定。没有单独保存运行时__file__清单，QA不声称此清单已经实测；run.head是祖先Root Git元数据，不能替代独立固定833身份。

真实trace顺序：turn_started → provider_result(tool_calls) → get_inventory成功（背包：空、revision2）→ provider_result(stop) → answer → turn_finished。两次requested/reported model均deepseek-flash，usage已知，汇总3458 input/207 output、model_calls2/read_tool_calls1，与API真实turn响应一致。实际limits：call20秒、1000output token、总45秒、model_calls最多3、format_retries0、progress_proposals1。

两个手动公开inspect发现r1_note_clue/r1_cabinet_clue。模型的submit_code/382提议statuspending、revision2、inventory空；clue_refs恰为已发现两项。用户request没有382/724/231，message hash与trace相同。首次confirm得到唯一receipt、revision2→3、柜门打开；第二次confirm的replayed=true、相同receipt/event_id/visible state、revision仍3。重复AI request也返回同turn_id/完整相同数据。全段前后快照仅新增这2call，runner计数/trace/HTTP/checks互相一致，confirm与两种重放没有新增模型调用。

这是强制首次get_inventory、显式请求R1密码提议、脚本确认的受控检查；两个inspect不是AI自主动作，两个confirm不是两个进度动作。脱敏trace省略完整出网prompt与raw provider envelope，所以本次核对public request/clues/server trace，而非新抓包。隐藏答案不出网的判断另依赖已读静态Runtime可见投影与这组source pin，不能宣称保存了完整出网原文。

## 证据复制、隐私和真人状态

原run目录：data/reproduction/A28-junction-20261006/clean/evidence/qa/20261006T043235515205Z-m3-real。Main实际0482fa exit0将4份脱敏JSON精确复制到evidence/integration/A28-real-20261006，并追加index。QA逐读原件/复制件和index SHA全部相同：

- run.json ef90c1d8404a6ee609850045d9343ba2cd6c0ac8603600ae21c0ee63e97dfdf2
- checks.json 019008a082b9f48629bfd7a6f4e193b2be7033fd345d9712f7110ae02326422c
- http-exchanges.json 83437b3faf7c9af799d19bb5eab89239b81b47d3bf8abe1ed32a1dbe99b547d7
- public-runtime-trace.json e326dab6551bd91301ca5b9afd09313dd9c6153ab787edc65abeab73f999c078

结构扫描未发现api_key/MODEL_API_KEY/authorization/X-Session-Token/token非脱敏值；runner公开数据/trace脱敏流程保持原样。没有为了匹配密钥值读取Root.env；不是对未知格式秘密的绝对断言。index中human_signoff和teacher_approval实际NULL，QA同样pending，不能以自动检查替代真人或课程签署。当前无新8真实评价审批/结果推断。

## 首次阻塞与后续准备保留

首次文件symlink relay实际c4f09f exit1：process_started=false、paid0、OSError/安全类别symlink privilege unavailable，凭据加载与子进程前停止。失败process SHA d0963248437b1ebb9d5c46377be8498c3c61c487d1f947644c9b76bffd8d5a85仍相同。原clean115741、旧marker及0-call machine证据不覆写；没有provider retry。新目录Junction绕开文件symlink工具限制，未改产品源码或guard。

初次0-call QA result保留evidence/qa/A28-real-result-20261006T043101848502Z/result.json SHA07d9e4b68a03e54a71205e58aa338e590170ed70ec37ce4958627a046ae120f5。该阶段报告原始字节SHA42c2a9d09d757f9d278b9f5cbbbfda3008a397f8e4b7a6b5a1cc22b3a5c48c50精确保存到本最终目录initial-zero-call-report.md；原QA index中的报告pin表示该历史版本，本页为任务继续后的最终报告，迁移映射在process.json显式记录。Junction只读GO证据preflight SHAe957ce1bc28bf820349d5fd3806e7737f7e53c895911994c71e5f8be2c8e4e34保留，不把它当真实执行。

## QA实际命令与结果

只新增tests/review_a28_real_result.py、当前报告及evidence/qa/A28-real-result-*；不改Owner/Git/原ledger/env或旧真实证据。QA helper SHA ad3abae105e8f4d7a6435ac0055b398b9e43aca9136fad648f8be923cfc4ef62。实际命令 `& 'C:\Users\liyh\.conda\envs\1\python.exe' -B -X utf8 tests/review_a28_real_result.py`，105检查、exit0、e56e64。实际结果只读schema检查219b3a/2b2aa8均exit0。QA硬拒绝socket连接和sqlite连接，没有模型调用或整套回归。

最终result.json SHA b357fdfc17eaf26b942e821dc20382c4a0de55e5766e59f04d74af38a932ded9，含85文件actual before/after、63clean/11Root maps和逐场景判定。process/index记录Main/QA命令、工具块/exit及证据hash；最终目录evidence/qa/A28-real-result-20261006T043600767538Z。

没有未解决的本段一致性Finding。真人操作/个人解释/教师审批仍未完成；实际module __file__清单、完整出网原文未保存是证据范围限制。必要只读验收完成，不再补模型请求或重复通过检查，稳定SOURCE STOP。
