# 普通“下一步”问法：独立验证与最终结论

最终状态：有限接受修复与记录内离线边界，QA SOURCE STOP。真实新两条在前一候选均成功显示；N01局部引导符合公开阶段，N02承接但“点电源箱的观察”暗示已移除的按钮，UI操作措辞与只解释依据的遵从程度为 WEAK，不能判整体回答质量全通过。最后仅模型侧观察措辞修正已经独立窄验，未进行新的真实模型复测。

最终候选 `candidate-label-fixed.json` SHA `50ccb3ec970e2bc1e8961f3ea9d1b4ed76234e302579b2d708be980a3c32ffef`，243source；相对实际付费候选仅 companion.py 改为普通观察“点击物件查看”的 wire 和 SYSTEM 文案，API观察标签仍是“观察”，所有其他242source不变。最终两个窄方法首次2methods/0.669秒 exit1：真实 Runtime+Store合成正常交付通过，静态方法的QA字符串预期遗漏中文引号而失败。首结果及脚本保留 `qa/20261018T153601756155Z-labels/`；只用新 `run_labels_narrow.py` 识别实际“不要求玩家寻找“观察”按钮”的语义，完成受影响静态方法，1method/0.266秒 exit0，`qa/20261018T153709582024Z-label-static-narrow/`。没有产品改动、已过HTTP重跑、全8重跑、第二次build或新增paid。

实际命令为 `C:\Users\liyh\.conda\envs\1\python.exe -B -X utf8 tests/companion-nextstep/run_labels.py evidence/integration/companion-nextstep/candidate-label-fixed.json`（exit1）与 `C:\Users\liyh\.conda\envs\1\python.exe -B -X utf8 tests/companion-nextstep/run_labels_narrow.py`（exit0）。窄验证确认 director观察入口与 visible_objects观察入口均用点击具体物件的措辞，take/interact等其他action label保持，纯转换不修改原public API，专用目镜说明仍在；当前实际公开stage中正确的“直接点击电源箱查看”合成回复经Runtime和Store均显示，read_tool0/proposal无/游戏核心不变，仅既有接受计数与revision+1。静态与合成输出只证明这层行为，不保证未来真实模型不会换词。

Main 实际新2calls费用上界0.00372936元（N01 0.00206、N02 0.00166936），累计0.97538384/10、剩余9.02461616，unknown3→3/新增0、未freeze、无重试。QA只读raw/display+预算脱敏摘要并校验8个artifact绑定、同session真实N01历史、逐字显示、两次hint/revision各+1及游戏核心不变；`qa/real-review.json`。N01准确区分维护已读与箱体未看，未虚构观察结果/独占物件；N02有事实依据和解释但附加旧按钮操作句，弱点保留。两条strictJSON/refs[]/无完整答案或代操作，不是“所有质量轴通过”。最终观察措辞调整发生在此付费epoch之后，不得把这两条重标为final source真实复测。

## 冻结候选实际离线结果

Main 冻结243 source，candidate SHA `cbc20d2a147cd15f15072a7223358af3cd5291a248ad46c523ac98298f785bc1`。首次实际命令 `C:\Users\liyh\.conda\envs\1\python.exe -B -X utf8 tests/companion-nextstep/run_regression.py evidence/integration/companion-nextstep/candidate.json`，exit1，8methods/5.491秒，7methods通过、一个新方法中5个 trace 字典预期失败。证据 `qa/20261018T153045999137Z-offline/` 保留。失败来自 QA 以为持久 trace 恰好两个字段；实际 Store 固定补入 call/model/usage/cost 的 null 元数据，类别均正确。这是 QA 协议期望错误，没有产品 finding。

只改新 runner 的 trace 比较，继续要求唯一合法 kind/code，额外字段必须恰好为既有固定 schema 且全 null，并继续检查没有原文。新命令 `C:\Users\liyh\.conda\envs\1\python.exe -B -X utf8 tests/companion-nextstep/run_narrow.py evidence/integration/companion-nextstep/candidate.json`，exit0，1method/1.191秒；证据 `qa/20261018T153140348851Z-trace-narrow/`。产品243和旧219路径均前后一致；没有第二次完整八方法全绿声明，不重复计数。

联合实际覆盖十四个公开阶段三种普通问法的合法局部动作、未放玻片/空背包早R2的两轮合成交流、真正why/线索格式关系保留相关记录；已发现钟面21:17正常表达允许，未知21:18/未发现钟面/柜码/完整登录值/条件密码指代仍拒绝。正常 Runtime 结果与独立伪造 Runtime 的 Store 校验均验证边界；拒绝后完整 visible state 包含 revision、提示次数/级别、背包和游戏进度不变。正常交流只按既有规则增加提示次数与 revision，没有 proposal/read-tool/自动行动。strict JSON、内部码、代操作和不可用引用仍拦截，持久诊断只带 FORMAT/CONTENT/REFERENCE 固定类别和空元数据，没有被拒绝原文。四个旧窄方法复用整组猜测0call、USER/PASS/引用、freepreset、legacy幂等兼容。

Main 唯一 build/typecheck exit0 是 Main 证据，QA 未运行或重复。QA 只读核对 Frontend stopped 分支：伙伴失败仅渲染一条原因，替换本轮通用文本并隐藏重复 stop-reason；计数/进度文案有上述实际 API 证明。本轮没有浏览器呈现验收。保留已有 Starlette/httpx deprecation warning。

真实调用预审当时 inline Python exit0，13checks/issues[]，`qa/preflight-review.json` 绑定冻结候选、执行器及预览哈希；最多两个新样本、0.16元，本轮预览 reserve上界0.105296元。Main 使用合法10步公开状态clone，N01普通下一步，N02仅在N01实际被接受后替换同session真实历史并重算上界；不重试、不重放旧unknown、不改玩家游戏DB。该预审阶段只给范围内执行GO，当时尚无真实质量结果；实际两条后续结果见本文开头，QA自身paid0/canonicalDB0/network0。

限制：用户被拒绝 raw 没保存，近期五条脱敏metadata也没有 exact-nextstep 匹配，因此不能称完整复现旧失败或确定唯一触发器。Main进一步只读检查的运行backend启动时间晚于上一修复commit，不能简单归因旧进程；metadata追加不改变冻结source。当前服务无reload，最终应用修复需要用户重启启动器，QA不停止正在玩的服务。钟面带“是不是/对吗”的问题仍可能触发原有整组猜测问题检测，本次只修输出中的窄钟面误报；自由文本边界仍是启发式。

## 以下是执行前准备记录

状态：仅只读审查和准备，正式执行 0；等待 Main SOURCE STOP 与冻结候选。用户补充“设备实验室，还没放镜片”，实际玻片交互属于 R1，不能据口述泛称把失败归到已登录 R2。真实失败 raw 尚未提供给 QA；`MODEL_INVALID_OUTPUT` 是多种格式/引用/内容拒绝共用结果，不能凭它声称已经完整复现或确定根因。

后续 Main 的 `local-diagnosis.json` 脱敏只读结果实际显示：近期五次失败都在 R2，电源箱 CLOSED、电脑 OFF、显微镜 EMPTY、背包空；已发现记录/钟/铭牌/维护说明四条线索。五条 `question_exact_nextstep` 都为 false，不能声称检索到了用户口述的同一问题。QA 没有读取原 DB。新正式脚本 `run_regression.py` 准备四个新 method 加四个旧窄回归，共八个；十四个公开阶段的三种普通问法归在一个纯内存 method，不冒充四十二个独立测试。新真实 N01/N02 预览由 Main 控制，QA 仅只读审查。

当前只读发现两个风险：model-facing director 只保留焦点名称，丢失本地公开目标中的动作类别/用途；“下一步怎么做”没有命中现有 procedural 过滤，可能混入与当前一步无关的已有线索。两点是风险审查，尚不是实际失败的确定归因。现有前端 `MODEL_INVALID_OUTPUT` 文案使用“建议/未执行任何建议行动”，与只读伙伴模式不符。

最小正式计划使用新隔离用例，不改旧测试/证据：

- 公开状态矩阵覆盖起始、已读记录/钟、已观察显微镜但未持玻片、玻片已观察待拿、已持未放、已放未读、柜锁接受未开；早 R2 箱体各阶段及已供电电脑初期。每个目标只核实一个当前合法公开步骤，不把预设文本或完整路线送入模型。
- 对“下一步怎么做/现在该做什么/我卡住了”与已放置后的变化，验证上下文确实反映背包、当前公开动作；明确“为什么/关系”仍保留所需证据。模型回复用合成桩，只证明交付通道允许正确的局部自然回复，不证明真实模型会生成它。
- 真实 Runtime 结果与最终 HTTP 分别观察：合法放玻片说明可以显示、proposal 为空、工具调用 0、游戏核心不动；被接受的交流按既有规则只增加提示计数与 revision。
- 坏 JSON、内部码、未知引用、代操作声称、完整答案等仍拒绝；通过正常 Runtime 和独立伪造 Runtime 的 Store 校验分别证明拒绝后完整公开状态不变，含提示次数、提示级别、revision、背包和游戏进度。失败文本应称“回复/交流”，不暗示确认或执行行动。

不重复全后端套件，不把 build、JSON-mode 或 API 测试通过当真实回答质量通过。若获授权进行新的真实样本，逐条单独审查实际原文、最终显示、当前状态和交付结果；QA 自身不联网、不读真实 DB/密钥、不发付费调用。

文件：`tests/companion-nextstep/prepare.py`、`run_regression.py`、本报告、`evidence/integration/companion-nextstep/qa/preparation.json`。实际准备命令 `C:\Users\liyh\.conda\envs\1\python.exe -B -X utf8 tests/companion-nextstep/prepare.py` 三次 exit0；最初 AST1、后两次 AST2，旧219文件快照，formal0。此前首次两条默认 shell 只读命令均在进程创建前被 helper setup refresh 拒绝，未执行；改用显式升级权限后只读检查成功。一次查看尚不存在本轮 plan 的命令 exit1，无状态变化；后续批量读取同一路径产生找不到文件提示但该批最后命令 exit0，不隐去这一准备查找失败。正式结果尚无。
