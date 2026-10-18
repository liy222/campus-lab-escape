# AI伙伴自然讨论：独立定向QA

结论：Main冻结候选 a3966227ee5d6f85303ddda6577e90324d6e4731c1c866fe5c8b8be18001a5c1 在约定范围通过，无未关闭产品发现。Owner开发检查未计入独立结果。

实际命令（D:\深度能力，显式require_escalated）：

- C:\Users\liyh\.conda\envs\1\python.exe -B -X utf8 tests/ai-companion/run_api.py evidence/integration/ai-companion/candidate.json：首次12methods/8.988秒，exit0；新8、旧preset2、旧legacy2，failures/errors均0。不另报未单独统计的subtests，不宣称旧全套绿。
- C:\Program Files\nodejs\node.exe tests/ai-companion/run_browser.mjs evidence/integration/ai-companion/candidate.json：exit0；一次typecheck0、一次生产build0，桌面Chrome13条记录、issues[]。记录包含清理，不能称13个独立断言。

证据分别在 qa/20261018T104302627701Z-api/ 和 qa/20261018T104317562Z-browser/。运行前后243源码rawhash匹配；73既有测试路径未改。无失败正式epoch、重复套件或重复构建。

真实HTTP模式、Store、Runtime、上下文及最终校验保持实际产品路径；仅测试专用request factory跳过DeepSeek构造器，complete返回合成响应并禁外网，不创建或读取canonical预算库。捕获当前问题、最近3成功问答、3合法动作、已知线索与结构化公开Director；去除动作arguments/observation。自然短文在最终HTTP保留，未被模板覆盖；tools=[]/none、单调用及合成usage数值一致。凭据误粘已脱敏，不进入模型载荷或events/ai_turns/receipts。恢复新generation后清旧历史，保留保存的计数/预设等级。

完整码（含全角/分隔/中文数字）、登录组合、四设备顺序/ID、线路数组、隐藏故事名称、虚假已执行、未知refs/多余字段/超长等样本被阻止。完整猜测判对错本地0call/no-count、不入聊天；无数字的“是的，你猜对了”也不能绕过。正常“墙钟21:17是什么意思”“输入4217没有反应怎么办”实际发起一次讨论；三种正常交流/局部关系短句被接受，未全拒绝。Director关键未完成操作和提前跨房方向正确，无自动推进。

Store按预留mode决定行为，不能被usage.provider/trace伪造；fake Runtime非法proposal/refs/stale被拒，read_tool被挡。无header实际DeepSeek类可进入companion，只有provider_name声称的对象仍preset。新mode进入摘要，换mode同ID冲突；旧DB加列默认existing、旧receipt无provider重放。幂等、inflight重复、手动推进race、失败和保存恢复重开均在定向范围通过。

桌面1280×900：mock无问题框且保留三级；真实模式有输入/key/发送说明并显示自然回复和usage，最近4条聊天；本地0call提醒明确显示且不入log。手动推进旧项outdated；切mock无输入，刷新/命名读档清key和聊天、恢复计数/等级。已人工查看全部4张实际PNG。滚动面板截图只显示当前可视部分，完整聊天/本地提醒由DOM和请求断言支持。

新增文件：tests/api/test_ai_companion.py、tests/ai-companion/{prepare_design.py,prepare.py,fake_runtime.py,qa_app.py,run_api.py,run_browser.mjs,seal.py}、本报告及新QA证据。未改产品、旧测试或旧证据，未提交。准备设计文本保存在qa/design-report-pre-formal.md；design-review.json旧reporthash属于历史设计epoch。准备期语法/hash核对exit0，一次引号编辑ParserError exit1（未执行Python）已修正exit0；末次报告patch机械写入遭工具拒绝后改显式提权写入，没有重新测试或更改正式run记录。

限制：验证问题管线和有限攻击边界，不认证生产provider构造/预算实现、真实模型文风/多样性/语义质量。自然文字guard是启发式，不是所有混淆答案/隐藏事实的完备证明。无全套127、手机、真实provider、历史用户DB或真人计时；paid/external/mobile均0。保留既有Starlette/httpx弃用和Vite大包warning。