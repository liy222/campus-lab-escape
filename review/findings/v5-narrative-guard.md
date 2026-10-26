# 有限叙述指令拒绝：独立 AI QA

2026-10-27。**当前426输入候选的有限合成专项通过。** 独立 AI QA 智能体执行，没有真人/教师审查、试玩或签字；不代表任意叙事语义或真实生成质量通过。

唯一正式命令为指定解释器 `C:\Users\liyh\.conda\envs\1\python.exe -B -X utf8 evidence/upgrade/v5.0/narrative-guard/qa/run_targeted.py --candidate evidence/upgrade/v5.0/narrative-guard/candidate.json --output evidence/upgrade/v5.0/narrative-guard/qa/run1`：`00ba27` exit0，**43/43通过**，JUnit4.117秒，未重跑。`078717` exit0只读终态/有限隐私，末次封存命令exit0。

固定8拒绝/10保留例分别检查story及三个房间description，共32拒绝/40保留断言；另核对换行格式、合法文字不被NFKC/空白处理改写、空白名不造空target且空名称仍Schema拒绝、item/clue改名及正则字面值、名称含动作词与同名坏句交叉、strict JSON/Schema先于guard、拒绝不进Host helper、合法参数/结构/Host说明不变。名称本身不扫描；alias资格校正不等于拒绝坏名称。独立合成ProductionService+MockTransport仅一发后worker MODEL_INVALID_OUTPUT/no-level，未进入helper或compiler；显式合成旧完整定义含坏故事，archive/reload原文字节/hash保持，不走新生成guard或模型。

当前bundle `bac38ee3696e95545c46959c2db7a0f287e7e2da30844742d96afadb14f00ae6`、426输入及before/after匹配。旧实际422相对当前仅两项获准产品源码变化，属于历史真实样本，不能回填为当前通过。旧测试/helpers不改；Owner初始检查、两次alias窄修、39→41→43准备记录及额度中断均是开发/准备，不增加正式运行次数，原件保留。当前已知坏句用公开引用＋明确合成有效参数验证，未读取/重放旧真实原稿或private4。

隔离门外网/config/非TEMP DB尝试0；标准库socketpair内部IPC15，非provider请求。24份观察记录只含受控合成数据、计数/布尔/hash。原output/JUnit有限凭据模式检查0（公开合成CANARY除外），未打印整段日志，不需脱敏；不保证所有编码。无真实provider/付费/Key/liveledger/用户DB/私有实际参数访问，无18proof/79套件、build/UI/eval。

结论仅限policy revision1规定的可识别子集：明确不支持的材料返还指令被拒绝，局部否定、历史/失效引用和规定保留例保持。单独“钥匙也不必带走”仍按歧义保留，不当成强制丢弃。其他同义、双重否定、跨句/陌生语法、名称/故事/氛围仍可能误导；没有误拒率、真实有效生成率或普遍质量证据。原P2/TXT-C6历史OPEN不自动关闭；严格拒绝仍消耗未来另行批准的调用，无修补、回退、补调用或自动收费重试。

新报告/result/seal SOURCE STOP，无产品/旧证据改写，不提交、不推送。
