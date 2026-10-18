# AI 伙伴自然讨论：独立 QA 设计审查

状态：只读准备与设计建议，尚未形成实现接受结论。未执行产品测试、构建、浏览器或 provider 调用；正式验证等待 Main 冻结候选及明确 GO。旧提示 QA 已封口，其结果不用于认证本次新增能力。

已阅读 `backend/app/ai/{runtime,context,provider,types,hints}.py`、`backend/app/storage/ai.py`、`backend/app/api/routes.py`、Assistant 当前真实模式文案，以及 `tests/api/{test_m3,test_play_ai_settings,test_upgrade_v34,test_hint_flow}.py` 中相关边界。此次仅新增 QA 准备文档和快照摘要，不修改产品、旧测试或旧证据。

## 必要架构约束

1. **模式必须由服务端在预留轮次时确定并保留。** 当前 Runtime 和 Store begin/finish 只凭 level3.4 分支，单改其中一处会造成模板重渲染吃掉自然回复，或非可信输出逃过模板约束。应使 preset/companion 模式进入可信 reservation，并兼容旧行默认行为。最终模式不能来自模型返回的 usage.provider、trace、答案或任意客户端 body 字段。请求重放应返回原轮次，不因为重放时 header/key/服务配置变化而重新选择模式或调用模型；具体冲突政策须在实现报告写明。
2. **真正的最近问答需要新清洗路径。** 当前 safe_history 只记录 AI answer，不记录该轮玩家 question；build_context 则保留完整历史，没有最近窗口/长度界限。建议 companion 专用受限窗口，保留经过脱敏的问答配对和必要已完成动作，不能把整个 event/request/result、session token、headers、内部 trace 或失败请求当作模型事实。若从 ai_begin.request_json 取问题，应与已完成轮次可靠配对；重放不重复历史，pending/unknown/旧 generation/未来 revision/其他 session 不进入上下文。
3. **Director 仅依赖已公开状态。** 未完成目标必须根据当前 visible objects、observed IDs、inventory、device/puzzle/progress、已知 clues 选择，不能从后台答案、未发现线索或全流程剧透生成事实。早跨房应给合法回访方向；猜中柜码、登录或终检后，不追补已经完成目标的历史条件。完成动作和建议动作应明确区分。优先给一个方向或一处关系，不能把 Director 当作自动执行引擎。
4. **Runtime 与 Store 都要守只读和回复边界。** 不能把 legacy 通用 runtime 直接用于新版：它允许 inspect 自动发现及 progress proposals，validate_final_content 只检查结构/已知 refs。新版自然讨论应传 tools=[]、tool_choice=none，使用阻止 read/proposal 的 callback；Store 按可信 mode 再做共享终验。即使替换整个 Runtime，fake answer/refs/proposal/read/stale 也不能绕过最终 authority。自由文字的校验不能仅靠 prompt 宣言。
5. **语义安全边界应明确而不过度承诺。** 至少覆盖未知物件/隐藏故事、未发现线索文本、完整柜码/登录答案组合/四设备顺序/固定线路角度数组、虚假已执行及系统/密钥回显。测试应包含换分隔符、全角数字、中文数字、JSON 数组、设备名称/内部ID、用户要求原样复述答案等显式攻击，同时保留“第3位”“前两位”“相邻端口”“已知单个设备”的合法短讨论。有限规则与攻击样本不能证明所有自然语言均安全；报告应写明此限制，不把正则命中当作完备语义验证。
6. **现有计数、幂等、保存与预算须保留。** companion 成功是否计提示次数、失败时强度是否保存、无当前 topic 是否仍可讨论、读档后最近对话是否清空，都应在正式前确定，测试依具体政策。不得让新分支绕过 canonical provider/model、budget、timeout、usage真实性、unknown reservation tombstone、auth 或 restore/stale guards。API Key 保持请求级短暂使用，不进入模型内容或持久化；旧 key 从历史复发也是泄漏。

## 定向正式验收提案

| 范围 | 必需证据 |
|---|---|
| 真实模式载荷 | 使用实际 HTTP deepseek header 及 synthetic key，替换 provider complete/transport 并禁外网；捕获当前问题、至少一轮最近问题与答案、只公开已知上下文、受限 Director 目标；明确没有私有答案/未知线索/credentials；tools=[]，无额外工具调用。 |
| 回复有独立内容 | fake provider 返回符合规则的短中文句，最终 HTTP/界面保留其自然文案而非 TEMPLATES 固定重写；不同问题确实进入不同载荷，最近上下文去重且有明确边界。它证明管线，不认证真实模型聊天质量。 |
| 目标正确性 | 初始、玻片待取/待放/待读、柜码已接受、线路已过、电脑已登录未读、缺纸/卡的提前 R3、终检已过未离开；含猜中答案缺推理线索的合法分支。只针对重要阶段定向取样，不重跑全视觉路线矩阵。 |
| 攻击样本 | 用户/历史/场景注入、完整答案及变体、未知 refs/隐藏事实、伪完成、proposal/tool_calls、malformed/oversize/non-string；fake Runtime 直达 finish 的同类攻击必须也被挡。保留正常短句及部分关系作为负对照，避免全拒绝。 |
| 服务端分流 | mock 仍原18+next_step、免费且无问题依赖；header/usage/trace伪造不能把 preset 改成自由输出；absent-header兼容与旧DB mode默认行为按最终设计验证。 |
| 状态与统计 | 临时DB有效新请求/同ID重放/重复inflight/stale revision和generation/provider失败；只读 gameplay/knowledge 未推进，计数按明示政策。必要一次named save/restore/reopen检查保存状态及conversation generation隔离。 |
| UI | 一次 build、桌面真实 Chrome：默认mock无框；真实模式有问题/key、明确实际发送范围及费用，synthetic fake transport后显示安全自然回复；mock切回、失效/失败反馈、只读与必要save/restore/reload。无手机、真实付费请求或额外无关矩阵。 |
| 回归范围 | 不改原测试。只选仍适用 auth/key/request isolation/budget/replay/readonly 方法；旧“真实模式仍只选题/忽略问题”的断言若过时，明确排除并由新需求测试取代，不宣称旧全套绿。 |

## 验收前待实现报告明确

- 模式权威来源、旧DB迁移默认值及 absent-header 行为；同请求不同 mode/key 的 replay/conflict 政策。
- 最近问答窗口（条数/字符）及恢复后的对话政策，问题与答案的配对来源。
- companion 提示次数/强度策略，以及哪些正常回答算接受；无当前预设topic时的讨论行为。
- 自然输出结构/长度上限及共享 guard；可允许的局部关系与禁止的完整答案界限。
- UI fake provider 的本地注入入口必须使用测试专用服务，不增加产品测试后门。

实际操作：通过显式 `sandbox_permissions=require_escalated` 的 PowerShell 读取以上文件并搜索相关方法，返回 exit 0；搜索发现不存在的 `backend/app/ai/policy.py`，不视为产品失败。新的 prepare_design.py 只计算源/旧测试哈希和记录当前 HEAD，不 import 产品或执行测试。后续真实命令、exit code、失败 epoch 和原始脱敏证据将另存新 QA 目录。当前正式测试 0、构建 0、浏览器 0、付费调用 0；不提交。

## 设计 GO 后的准备进展

Main 已明确 durable behavior_mode、新 mode digest/旧 receipt 兼容、一次 tools=[]/none 讨论、成功计数+1且不改预设等级、最近3成功问答+3动作、恢复清历史，以及整组答案判定请求本地0call/no-count、不进入成功对话。正常“墙钟21:17是什么意思”“输入4217没有反应怎么办”不应因为出现数值被一概当成核对答案。新测试按这些政策准备；不复用旧“真实模式只选题、不发送问题”的预期。

新增准备文件为 `tests/api/test_ai_companion.py` 和 `tests/ai-companion/{run_api.py,run_browser.mjs,qa_app.py,fake_runtime.py,prepare.py}`。8个新 method 准备覆盖结构化Director关键阶段、自然文案/真实载荷、多问题与历史裁剪/脱敏/恢复、显式攻击及正常短交流、可信mode和旧DB迁移/重放、并发/失败。准备选择旧 preset 2 methods 与 legacy 凭据/隔离 2 methods；不执行全套。桌面runner准备一次build、最多4条交流UI、实际本地提醒及命名存档恢复。

测试专用 factory 构造真实 DeepSeekProvider 类型但跳过其构造器，替换 complete 并禁外网；route 模式决策、Store、Runtime 和终验保持真实。它不会创建或读取用户 canonical budget DB，明确不认证生产 provider 构造/预算实现或真实模型质量。测试服务额外观察接口只存在新 QA app，产品无测试后门。

实际 `prepare.py` Python AST 5文件、旧73路径hash核对 exit0；Node `--check tests/ai-companion/run_browser.mjs` exit0。准备期一次带引号的机械编辑遭 PowerShell ParserError exit1，Python未执行；已用literal here-string修正exit0，记录在 preparation-notes.json。此项不是正式测试失败 epoch。正式运行仍为0，等待 Owner SOURCE STOP/Mainfreeze。
