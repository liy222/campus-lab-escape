# 《逃离校园实验室》v5.0正式构建计划书

版本1.8；2026-10-27第14节有限结构多样性已完成实现与独立联合验收；第15—17节的B职责、有限守卫与提示澄清保持，普通Git同步状态另见STATUS。

版本1.2修订来源：2026-10-24按用户选择的“程序结构+AI内容与谜面参数”修订，保留2026-10-23实施登记与2026-10-22设计讨论来源。用户于2026-10-23要求开始执行，并持续正常提交到GitHub。此文定义范围和验收，不是执行证明。

## 1. Intent / Problem Frame

来源：用户转述老师建议“自由生成密室关卡、Web与API Key安全验证”，随后用户确认校园不限实验室、自由描述、完整关卡1—3房间、三难度、用户名密码私人账号、临时BYOK、本机运行、手绘素材复用与可追加目录。唯一人类开发者liy222。教师审批、真人试玩和签字均未发生，不能由程序推断。

问题：固定主线重复性有限，原会话没有账号归属。目标：玩家生成、保存、游玩自己的校园关卡，重登录恢复，其他账号不能访问。工程取舍：受限数据生成、服务器验证执行，保留原系统。

六环输入链：Intent记录→本节问题框架→第3/4节规格与验收→第6节任务卡→第7/8/9节Harness及边界→候选绑定代码/测试/日志。每环稳定产物是下一环输入。计划状态Planned，真实结果另存。

## 2. Baseline / Scope / Facts

- 交接HEAD fe62d5960b75d8e7c74a60234f767eaa5570118e；最近产品9eeea511673867402b269124b6d1b739eb25a68d。画面4.2、规则3.4.0、API/Schema1.4.0。旧13业务路由和历史规则保留。
- 已有三房间手绘、多阶段规则、线路/顺序小游戏、多时刻存档与删除、免费三级提示、真实伙伴；沿用Store事务/回执/revision/generation、SQLite和Canvas桥接。
- Python C:\Users\liyh\.conda\envs\1\python.exe，现有3.14.7；不重置环境。Git身份liy222 / 177762329+liy222@users.noreply.github.com。原数据库、密钥、环境、未跟踪文件和历史证据受保护。
- 新增账号/归属、数据关卡内核、生成任务/准入、动态场景、新合同和专项验证。排除社区、编辑器、多人同局、公网、云存档、生图、Actions、其他供应商和旧存档迁移。
- 当前AI仅有限样本接受；最后措辞修改仅离线验证。不能把旧QA视为最新源码通过，不能声称全部自然度/防剧透/事实正确。既有构建警告保留。
- 原供应商默认最多1000输出tokens/20秒，伙伴600/20；生成需要独立受限6000/60配置，不能提高伙伴限制。
- F01基线与Git只读核对；F02 Argon2依赖已安装但需项目锁；F03 2026-10-22预算只读摘要未冻结且3条历史unknown，今天未重复查费用。
- D01新版独立库，不迁移；D02声明式数据；D03保留评价严格门控，用户已选，不豁免旧unknown。
- A01 6000tokens容量，AI Owner T3验证；A02素材适用，Frontend T4验证；A03 25000状态/5秒，Backend T2/E1验证；A04密码依赖兼容，Backend T1验证。失败不能预填通过或自动增额。
- OQ01可用真实凭据未读取，阻塞真实样本不阻塞离线；OQ02旧unknown不本轮追查/改账，阻塞第6次付费评价，不阻塞产品实现与离线QA。

不变量：服务器权威；新库隔离；每请求不可变规则上下文；幂等和进度隔离；模型无可执行权限；恢复不用LLM；未知保留预留；失败与旧证据不覆盖。

## 3. Specification / State / Interfaces

### 产品与领域

登录后经典主线/我的关卡；主题1—2000字符、房间1/2/3、easy/normal/hard；临时Key。无Key可玩旧/已生成关卡及免费提示。每用户每关卡一份当前会话，重登录继续；reset原定义，保留手动存档；新生成才调用。

四机制：非消耗道具匹配；数字拼接/位置读取/符号映射密码；四设备顺序；现有3x3线路可信模板。谜题=房间数+1/2/3、最多6；多房至少1跨房依赖；normal至少1双线索；hard至少2组合推理且依赖链>=3。每房<=8主要物件、出口另计，items<=4；错误不销毁资源，开放通路往返；显式EXIT才won。结构难度不等于真人时间。

模型现在提交GenerationContent，不自行设计引用/依赖/槽位。Host选择一次版本化生产蓝图，严格验证指定槽位文本与typed数值/排列/映射参数，按事先合同组装LevelDraft；坏填参不补写、不修值、不用fixture或历史关卡替代。完整Draft仍不可信，只含白名单数据，不含答案/脚本/HTML/SQL/路径/外部URL，继续由原编译器形成不可变CompiledLevel；服务器计算答案与权威线索。VisibleState仅公开事实；ValidationReport含hash/version/witness且不发给玩家。

准入：严格JSON（重复键/非有限数/深度/额外字段）→已选GenerationContent exact槽位/类型/值域→声明式组装Draft→原Draft形状/引用/唯一性/资源→谜题参数与材料充分性→依赖无自锁→25000抽象状态/5秒规划→真实领域动作回放→合法槽位布局。规划先获取必要材料，不以后台答案跳过线索；线路宏展开并实际回放。超限=尚未证明可解，不称无解且不可玩。JSON mode仍需拒绝空内容、截断和语义错误，无自动修复付费调用。

Store共享事务/迁移/回执；每请求绑定可信principal、session、冻结rules。禁止全局Store.rules变更。认证先于私有回执。新版无旧能力token旁路；classic绑定3.4规则，generated绑定定义。保留原动作/控制/存档的各自幂等与generation顺序。

### API v2

前缀/api/v2，保留ok/event_id/data/error。GETauth/csrf；POSTauth/register/login/logout；GETauth/me；POST/GETlevel-generations及GET/{id}；GETlevels及GET/{id}；GET/POSTsessions；GETsessions/{id}/state；POSTactions/reset；GET/POSTsaves；POSTsaves/{id}/restore/delete；POSTai/turns。游戏修改体request_id/revision/generation；生成体request_id/theme/room_count/difficulty，Key仅头。相同请求返回原任务，换参数409，Key不进入持久摘要。不把所有响应强制解释为visible_state。生产不挂载旧匿名业务路由。

401未登录；404私人资源不存在/不属于当前用户；403CSRF；409冲突；422结构；413过大；429限额；502非法供应商输出；503不可用；504超时；错误无堆栈或私有定义。

任务pending→generating→validating→ready/rejected/failed/unknown；仅ready正式关卡。无名额429不持久排队，不存Key。重启pending未发出→failed，generating→unknown，validating→failed；不重发。logout后在途生成只归原owner；伙伴迟到需再次检查身份/版本，不写新进度。restore/reset新generation，delete不改当前事实。

### 账号与安全

用户名ASCII字母数字下划线3—24统一小写唯一；密码12—128原样，Argon2id19456KiB/t2/p1随机盐。锁定argon2-cffi25.1.0、bindings26.1.0、cffi2.1.1、pycparser3.0，不冻结全环境。随机会话token数据库存hash；HttpOnly/SameSiteStrict/host-only/Path=/api/v2 Cookie，闲置30m/绝对8h，登录轮换退出撤销。账号5失败/10m、来源30/10m冷却60s；注册10/10m；hash并发2，不永久锁号。

匿名CSRF10min保护注册登录，登录轮换；已登录修改需绑定CSRF和X-Auth-Context及精确Origin。Origin:null/错误Host不合法。不自动刷新认证并带旧Key重发；跨页广播仅身份变化，Key/聊天/旧响应清理。Key只页面内存/请求/供应商认证头，刷新/免费/换账号/退出/会话/reset/restore清理；不进入任何存储、模型内容、URL、普通日志、错误、证据、Git；误粘贴先替换。固定官方DeepSeek地址和deepseek-flash；不重定向、不环境代理、不换供应商。

生产127.0.0.1:8001同源，dev5174代理；Host/Origin明确配置，不信转发头。CSP脚本self无inline/eval，样式可inline；frame-ancestors none、nosniff、私人响应no-store；仅静态dist-v5，禁止.env/.git/DB/源码暴露。请求16KiB，模型输出64KiB/深度32。本机HTTP明确边界，LAN/公网另案HTTPS/Secure；被攻陷OS/浏览器/扩展/本机管理员不在保证内。ASVS5.0.0适用子集：认证6.1.1/6.3.1，会话7.1.1/7.4.1，授权8.1.1/8.2.2，不称全认证。

### 展示、素材、提示

通用Phaser固定视角+现有art/桥接，经典场景保持；模型只选登记role/slot，服务器坐标。单一资源JSON记录id/version/url/尺寸/bbox/role/variants，前后端共用，后续追加不删旧。固定clockFace角度/经典符号不可用于生成权威线索，只按已发现公开材料绘制；冲突图案遮罩或不登记，PNG原字节保留。无Key不生成但可游玩。当前中性背景不宣称大量专属校园美术。

免费L1方向/L2关注点/L3局部关系，当前公开阶段选题；伙伴最近3轮成功问答+3无参动作，公开输入、不执行动作，UI最近4轮。动态线索总量，探索评级90%/70%，其他沿用；自然语言质量仅限实际样本。

## 4. Requirements / Acceptance Matrix

以下全部MUST，初始Planned。证据基址evidence/upgrade/v5.0/<candidate>/<run>/；各记录需commit/hash、case、实际命令/exit、结果和局限。主责实现不等于独立QA。

|Req|可观察要求|Cases|Task|证据桶|
|---|---|---|---|---|
|GEN-01|主题/规模/难度形成对应关卡；Host限定结构，AI生成真实内容参数，真实与离线分开|P02|T3|generation|
|GEN-02|准入失败不可玩|N01|T2|admission|
|GEN-03|四机制/规模/难度约束|P02,N01|T2|kernel|
|GEN-04|失败/拒绝/中断/未知准确无重发|N03|T3|jobs|
|USER-01|跨用户交换ID拒绝且原状态不变|A01|T1|authorization|
|USER-02|重新登录/关页/重启恢复|P01,P03|T1|accounts|
|USER-03|密码/轮换/退出/过期/限速|N06|T1|auth|
|KEY-01|Canary只出现在允许认证传输|A04|T3|secrets|
|KEY-02|跨页与迟到不串Key/内容|A07|T5|identity-race|
|COST-01|并发重放至多一次/未知预留|A06|T3|budget|
|COST-02|时间/频率/费用/并发限额|N04|T3|limits|
|SAVE-01|坏定义/hash/版本拒绝且不覆盖|N02|T5|restore|
|SAVE-02|三时刻/删除取消/reset保留|P03|T5|archives|
|SYNC-01|旧rev/gen/换参重放无副作用|N05|T5|transactions|
|AI-01|提示伙伴仅允许公开上下文|P04|T5|ai|
|AI-02|注入不新增权限/失败不算成功|A05|T5|ai-boundary|
|WEB-01|恶意文本不执行脚本或任意资源|A02|T4|web-content|
|WEB-02|CSRF/Host/旁路/文件暴露阻断|A03|T1|web-host|
|API-01|严格v2合同和错误行为|N01,N05|T0|contracts|
|UI-01|目标视口触控/键盘/特写无漏点|P05|T4|ui|
|ASSET-01|登记素材/无固定答案串入|P05,A02|T4|assets|
|LEGACY-01|旧库/入口保留、必要共享回归|P06|T7|legacy|
|ENG-01|源码/上下文/真实执行绑定|A08|T0|identity|
|ENG-02|冻结输入的E1/E2/E3|E1-E3,A08|T6|events|
|EVAL-01|合同/引用/四状态/缺证不PASS|A08|T6|evaluation|
|DELIVERY-01|启动/恢复/回退/本人接管|P03,P06|T7|delivery|

SHOULD主题与素材一致，不匹配记录视觉限制；不降低MUST。

|Case|Given/When|Then|
|---|---|---|
|P01|A注册游玩退出，关页/重启重登|恢复本人不混B|
|P02|1—3房间x3难度9定义准入回放|约束符合且到EXIT，真样本另标|
|P03|早中晚三档/推进/读早/取消删/确认删/reset重登|正确恢复，只删选中，其余留|
|P04|多公开阶段免费及模拟伙伴|0调用/合法引用/计数历史隔离|
|P05|1280x720,390x844,812x375|44CSS目标、键盘、无漏点遮挡|
|P06|隔离经典主线及旧API相关回归|旧规则和存档兼容，不读旧库|
|N01|坏结构/引用/自锁/映射/超限|分类拒绝，无可玩记录|
|N02|坏hash/缺定义/错版本恢复|不改当前和他档|
|N03|空/截断/401/超时/发送后中断|分类保守无重发|
|N04|达到所有资源费用限额|拒绝无多调用|
|N05|旧rev/gen、同ID换参数|冲突/既有回执且无副作用|
|N06|错密码/过期/固定会话/连续失败|认证/轮换/限速有效|
|A01|B用A关卡/任务/会话/档ID读写|404且A状态不变|
|A02|脚本/SQL/穿越/URL/多字段|拒绝或文本，无执行/外发|
|A03|跨站/无CSRF/nullOrigin/坏Host/旧路由/敏感文件|拒绝；GET不推进|
|A04|合成Key与token成功失败全链|禁止通道零值，报告只CanaryID|
|A05|模型忽略规则/工具/答案/Key指令|权限不变，非法回答不计成功|
|A06|并发重复生成/动作/未知|一次发送提交、保留预留|
|A07|A页Key，B页换号，旧响应迟到|清理/拒绝/无串账号|
|A08|改源码/证据/版本/引用/注入|阻断或缺证，确定FAIL不被PASS覆盖|

## 5. Impact / ADR

前端增加账号和通用场景，防旧状态串入；领域参数化四机制，校验材料充分性；Store增加归属/定义/任务，用绑定上下文避免全局切换；AI新增生成profile但不扩大伙伴；素材排除固定答案；v2合同单列；新启动端口/DB隔离；证据不套用历史。

ADR01选择声明式数据+编译，拒模型脚本/仅换文案：可验证可复用，但非任意玩法。ADR02绑定Store视图，拒全局切换/复制后端：事务复用，需要所有入口检查。ADR03新库，拒旧库迁移：保护回退，旧档不在账号中。ADR04服务端Cookie+CSRF，拒浏览器持久Bearer：可撤销但跨页需处理。ADR05角色素材目录，拒运行时生图/固定场景：无生图费用，首版变化有限。ADR06保留评价严格门控，拒历史unknown例外：用户已选，真实评价缺口保留。决定按用户接受版本维护，后续偏差追加DECISIONS。

## 6. Plan / Task Cards

共同字段：Input本稿+交接+相关源码/合同；Evidence本轮新目录，实际cmd/exit/hash/局限；Owner只写分配路径，禁止历史DB/环境/证据改写；DoR依赖稳定；DoD逐项验收；失败停止受影响链，保留候选后窄修。正式QA只SOURCESTOP后。

|Task|Owner/允许路径|依赖/输出|Validation/DoD/Recovery|
|---|---|---|---|
|T0|Main根/本稿，Spec docsSPEC/level_design及contracts/v2，Delivery/QA各入口|基线核对→规格/状态/合同/矩阵/Harness|V0引用、26Req8Task20Cases；冲突冻结受影响任务|
|T1|Backend api/storage/main/deps，Frontend v5账号入口|T0→账号/CSRF/归属/私人经典|V1auth/P01N06A01A03；双账号+重登；停止新版回旧入口|
|T2|Backend domain/generated及新增blueprints，Spec合同|T0→Host蓝图/typed填参与原DSL编译/四机制/规划回放|V1kernel/P02N01；正常可解坏例拒；无模型补救|
|T3|AI ai生成/profile，Backend api/storage任务|T1T2→单次GenerationContent/组装及生成状态/幂等/限额/准入|V1generation/N03N04A04A06；通过才可玩无重复付费；未知不重发|
|T4|Frontend全目录，Delivery scripts/新启动新版.cmd|T1入口T2合同→通用画面/目录/同源入口|V2V3/P05A02；3视口/键盘/无答案串入；保留旧构建入口|
|T5|Backend saves/storage，AI动态提示伙伴，Frontend界面|T1-T4→定义存档/同步/提示/跨页|V1integration/P03P04N02N05A05A07；保留旧进度拒坏档|
|T6|Experiments experiments/v5，Evaluator evaluation，Main登记，QA复核|T2-T5稳定→E1E2E3/新合同3Claims/离线K校准|V4V5A08；保留旧标准，付费评价阻塞|
|T7|QA tests/v5/review/evidence，Delivery README/release，Main接受Git|所有源码STOP→独立验证/交接发布|V0-V6必要范围，关键MUST真证；失败保留窄修重验|

依赖T0→T1/T2→T3/T4→T5→T6→T7，共享文件不得并行写。每可运行里程碑正常commit/push liy222，新分支codex/，最终接受才发布tag。

## 7. Dual Harness / Repository Map

Runtime：记录实际Thread/Run/workspace可得ID，未知留空；Sol/high复杂开发/QA，Luna/medium机械任务，Main/resumed实际runtime不可独立验证；同刻最多2实施Owner，QA可准备不得对变动候选正式运行；只允许分配路径/现有CLI/必要官方资料，不读输出Key、不结束用户进程；模型0自动重试；失败定位后窄验；秘密、越权、预算冻结、新unknown、运行中源码变化停止影响链。

Project：AGENTS规范，PLAN依赖，STATUS实际状态，DECISIONS取舍，docs/SPEC与level_design行为，contracts/v2合同，backend/app真实规则，frontend展示，scripts启动验证，tests/v5新QA，experiments/v5实验，evaluation只读评价，evidence/upgrade/v5.0执行，review解释，release交付。路径均以D:\深度能力为根，不复制冲突权威。

配置修改代表回归：正常任务、禁止动作、生成不抬伙伴限额、旧入口/DB隔离、费用路由错误可解释；不自动跑全套或付费。恢复包current_state/last_verified_commit+hash/open_failures/decisions/human_questions/do_not_repeat/next_safe_action。

## 8. Source of Truth / Host / Visibility

范围=用户接受意图；行为=规格合同；状态=DB事务+规则；关卡=不可变定义hash；身份=服务端会话归属；执行=来源绑定命令exit/状态；接受=独立QA范围+Main记录+真实人类确认。冲突记录查明，不把实现改写成原需求，UI需同步，动画/模型自述不是真值。

Host负责认证、参数/资源授权、工具/费用、最终写、投影和审计；Agent只受限槽位内容/typed谜面参数或伙伴答复。Raw/Derived/Masked/On-demand/Prohibited：完整定义答案HostRaw、前端/伙伴Prohibited；生成器不回传编译真值；公开状态前端Derived/伙伴按需；Key仅输入者内存与Host请求Raw，所有模型/证据Prohibited；Cookie令牌仅传输/浏览器内部且DBhash，JS禁止；密码仅输入/认证且DBhash；Trace脱敏按需。来源/版本/user/session/generation绑定，换号/恢复/reset失效。

## 9. Validation / Trace / Budget / Stop

现有V0 contracts/check_contracts.py --output <新路径>（只结构旧合同），V2 npm --prefix frontend run build（v5 env+dist-v5）；待建设V0-v2 contracts/v2/check_contracts.py，V1 python -m scripts.check_v5 --suite auth|kernel|generation|integration|security|legacy --output <新路径>，V3同脚本browser，V4 python -m experiments.v5.run，V5已有evaluation.cli precheck/evaluate --release v5.0-engineering需新登记，V6 check_v5 evidence。缺入口=NOT_READY，不能PASS。Python指定解释器，测试先隔离SQLITE_PATH/AI_PROVIDER mock，禁止导入时开玩家DB；生产浏览器用独立账号/DB。Owner局部→STOP独立集成安全浏览器→共享旧回归一次→发现窄修；不重跑无关历史付费脚本。build120s/API浏览器每组300s超时未完成。

每Run包含Task/Req/Case、candidate+HEAD+source_before/after、合同/input/context、实际命令起止exit、状态diff/网络次数、usage/null/costupper/unknown、复核/局限。UTC存北京显示，秘密不Trace；模型Token未知不可造。CLAIM/STATIC/OBSERVED/REPRODUCED分开，hash不等于provenance。

限额用户1/global2在途，3/10m10/北京时间day；生成1调用6000/60s、整项90s；规划25000/5s；伙伴600/20s；自动重试0。

已授权验证：1房easy/2房normal/3房hard各1调用单项<=0.20元；伙伴当前公开阶段1次和真实上一轮追问1次各<=0.05。第6次评价原<=0.30，因3历史unknown保留严格门控不下发不挪用。目前最多5次<=0.70，原总上限6次/1元仍在，所有使用原10元账本。每次完整实际payload按原保守峰值预留检查；超限不发。失败/格式错/未知占次数，新unknown/frozen/型号异常/秘密立即停。凭据未配置继续离线不假冒真实。费用非账单，不包括无法取得的Codex开发消耗。

## 10. E1 / Change E2 / Counterexample E3

E1只变量Schema-only vs完整准入；固定候选/环境/输入/限额。9合法(房数x难度)、20错误(引用/依赖/语义/布局各5)、5超限中断另计；两算法每输入一次确定性比较，统计错放/正拒/误拒/unknown/耗时规模。完整坏例0放行、合法9可回放、超限分类准确。离线不统计推广不付费。

E2隔离预发布policy0.9普通不强制双线索→正式1.0强制至少1，与最终规格一致。T2冻结前定义/存档，T6有限改规则，旧定义hash/执行/档不重写；新不合规拒，旧能恢复不LLM。0.9只隔离演练无公开宽松入口。这是计划内Change，不虚构真实旧发布/新用户反馈。

E3主反例B读/恢复A存档：预期/实际/最小请求/状态前后/来源/修复/独立复核；已有防护记阻断，真缺陷保留修复链；失败对照仅隔离fixture不植入产品。其他恶意文本/Key/重放由专项覆盖不凑Finding。

## 11. Evaluator / Independent Review

V5-C1登记9正常准入回放和坏例拒；C2登记A/B端点隔离且无目标变化；C3三时刻原定义恢复与坏档不覆盖。每Claim冻结具体candidate、范围和证据，不称任意可解/绝对安全/全部AI好。

新v5可信合同/登记，旧A01-A28/冻结不改。复用engine/reader/严格Schema/引用/确定失败优先，薄适配多合同且仅Main固定登记，目标不能选路径/标准；不执行目标脚本/AGENTS/Hooks。原10MiB文件/16KiB片段/64KiB每Claim和路径防护保留。新版离线K1支持、K2失败、K3自述、K4注入、K5假引用、K6合法/非法NA，逐项预期实际且falsePASS=0；fake不是实校准。PASS/FAIL/INSUFFICIENT_EVIDENCE/NOT_APPLICABLE，MUST无获准NA；无真实判读不能把预检改成模型PASS。3旧unknown阻塞新付费评价，适配与离线可验，不称新真实语义评价完成。

## 12. Compatibility / Delivery / Human Responsibility

data/game-v5.sqlite只新版；启动前app标识/版本检查，非空非v5拒绝不迁移；旧game-v3.4等不碰。API2.0.0/定义1.0.0/执行1.0.0/policy分别版本，classic规则3.4。档绑定owner/session/levelID/hash/结构/规则/policy。缺失/不支持/坏hash拒且保留当前；checksum不是加密。新档旧版不识别、无自动迁移。未来迁移另定义backup语义。

启动新版.cmd→scripts.run_v5(待建设)，prod8001/dist-v5/v5DB，dev5174；检查依赖端口不自动重装/杀进程；Python改动重启。回退只停新服务、保留新DB、用原启动游戏.cmd/原库；不称新档可由旧版读。

发布门：设计26MUST20Case8Task完整；稳定来源/合同/API/build/browser/restore/经典必要回归真实，产品关键MUST真证且严重授权/Key/状态问题关闭；没真实成功生成不能验收真实生成。课程E1-E3/eval离线真证；付费评价缺口单列不称所有课程真实判读已满足。正常阶段commit/push liy222只选择明确文件，不提交secrets/DB/env/node_modules/raw敏感日志；不force、不Actions/部署。

本人接管：解释生成→准入→Store→公开状态及存档generation链；解释ADR；诊断真实/隔离标注反例；实际停止重启回退继续；指出未验证边界。AI披露实际活动、QA实际operator，人签/教师批准仅真实发生后填写。

本计划实施记录以STATUS和evidence/upgrade/v5.0为准；此文不预填测试通过。


## 13. 2026-10-24接受的生成职责修订（选项1）

用户在解释结构自由度下降后明确选择“那就选项1”。这接受docs/v5-generation-reliability-proposal.md中的B方向；不授权新增付费。本节优先于v1.1中模型直接提交完整Draft的描述；26条MUST、20个Case及T0–T7编号不变，R0–R4是其实施子任务。

### 13.1 What / Why / 权威边界

Host确定房间顺序、谜题数、前向依赖、资源引用、物件位置与配方，模型生成校园主题文本和真正改变答案的材料参数。首版是position_v1、mapping_v1两种资料结构族，覆盖九种房数/难度请求共18个精确合同变体；共同采用前向依赖链，不能称为18种独立拓扑或任意新玩法。选族由Host每次生成时随机选择；可控非负整数seed只供内部验证，不新增公开请求字段。

模型不再处理导致第三轮失败的全局引用连接；它仍决定数字源、设备排列、读取位置、符号排列/对应值以及额外谜题源序。素材、结构与配方选择范围有限，叙事是否贴切/有趣仍需有限实际样本；声明式结构证明不等于全部语义或真人难度认证。

### 13.2 稳定内部合同

content_version=1.0.0，与原Draft/definition/rules版本分别命名。根字段严格为content_version、blueprint_id、title、story、rooms、objects、parameters。rooms/objects恰好包含已选Host槽位，值仅name/description；不增删ID。schema中的版本/blueprint_id是const。文本长度与安全规则沿用原Draft边界。

position_v1包含四个单数字字符串digits及1–4的完整整数排列positions；存在基础顺序谜题时还需四设备完整排列devices。mapping_v1包含A–D排列code_symbols与单数字digit_map；存在基础顺序谜题时增加E–H排列sequence_symbols与四个互异白名单设备device_map。两族在5题时追加独立extra_digits，6题时追加独立extra_devices，各被合同规定拆为2+2两份concat资料。digits允许重复；排列、映射类型/值域严格校验，不接受bool/浮点充当整数。

1房hard为4谜题+1道具+3份共享兼容资料，恰好8物件。多房额外资料置于相应谜题房；初始资料与道具在首房，最后道具谜题形成真实跨房依赖。每份资料恰有一个可发现物件；不自锁或要求前房依赖后房。四机制按规模使用，4题以上覆盖code/sequence/circuit/item；其余规模不强求四者全部出现。原组合数/深度/规划/布局/原始答案泄露检查继续生效。

生产模块backend/app/domain/blueprints.py独立于make_fixture；只提供不可变蓝图、精确Schema、manifest及严格assemble。public API仍20路由，GenerationService保留worker参数调用兼容；同一次generate只选一次蓝图，消息和组装使用同一实例。原provider、6000/60、0.20元、0重试和经典/伙伴限制不变。合法2000字符的完整费用边界按新载荷实测，不沿用旧提示大小结论。

### 13.3 Tasks / 验收 / Change / 交接

R0 Main/Spec更新本稿、SPEC、level_design、DECISIONS、新内部合同说明，保留旧规格和真实失败的Git/证据来源。R1 Backend只新增blueprints.py及generation-content.schema.json/build_generation_content.py。R2 Main/AI仅改AI/v5.py生成提示与GenerationService；伙伴投影/保护、编译器/API/Store冻结。Frontend仅Workspace.tsx解释文字；Delivery待实际QA后更新README/release。精确Owner清单与实际派发见evidence/upgrade/v5.0/blueprint-generation/plan.json。

R3独立QA只在所有Owner SOURCE STOP与Main冻结之后执行：18变体及两组受控参数的编译/witness、独立预期答案/参数变化、typed/raw/extra/missing/恶意内容拒绝；真实ProductionService+MockTransport/fakeledger一发→原API准入/动作/档案/恢复；旧完整定义不调用新生成。新内部合同重建检查，公开合同不改；一次受影响前端构建和生成表单的有限布局核对。旧test_generation/prompt中已被本合同替代的expectation可以明确修订，禁止放宽Key/预算/一次调用等保护或改写旧运行结果。旧53-source有限评价不覆盖新生成模块，不自动重登记或伪称实际判读。

R4实际模型质量仍须新的来源绑定请求预检及明确有限授权，至少针对之前失败的2/normal与3/hard；当前无授权。合成参数/MockTransport/代码证明均不填成真实生成成功。无任何fallback/修稿/补调用；秘密/越权/账本冻结/新unknown即停，求解超限仍PROOF_UNKNOWN。依赖与回退：先稳定R0/R1再接R2，完成R3后普通liy222提交/推送；保留旧入口/库/定义/档与过去真实结果，不迁移、不重算旧hash。最终人类和课程确认仍仅按实际发生记录。


## 14. 后续阶段：多套合法骨架与结构多样性

### 14.1 已确认的后续目标与顺序

2026-10-25用户明确要求将“增加多套合法骨架，同房数、同难度下改变线索分布和解谜先后”写入计划。本节作为当前方案完成后的后续阶段；本次只确认路线目标，不代表结构功能已经实现、立即启动实施或获得新的付费许可。

依赖顺序：当前物件说明方案的职责确认、实现与必要独立验收、交付提交 → 本节SD0细化与冻结实施范围 → SD1–SD3实现/独立验证 → SD4交付。当前物件文案A/B的选择状态沿用原记录，本次后续目标登记不替代该选择，也不把结构扩展混入TXT0–TXT4当前任务。

### 14.2 范围与变化定义

- 初期采用有限、版本化的多套合法骨架。固定相同房数与难度时，能够选择不同的资料放置、前置依赖或解谜先后；不是只改变名称、故事、数字答案、显示顺序或资料关系族标签。
- SD0先列出3房数×3难度的可行性矩阵。目标是每个支持组合至少2套结构确有差异的合法骨架；至少一组同参数样本的依赖关系或可执行解谜先后不同。若既定数量、深度、跨房等约束使个别组合达不到，必须在实施前列明限制并确认范围，不暗中降低目标或放宽准入。
- 资料分布同时检查房间归属、场景槽位与发现/解锁条件。单房间以房内放置和发现关系变化衡量，多房间可增加受约束的跨房资料分布；任何变体均不得把必要材料或钥匙锁在自己依赖的装置之后。
- 结构签名须忽略AI文案、参数数值与随机ID，归一比较房间归属、谜题机制、依赖边、资料引用及放置关系。验收需分别证明“资料分布变化”与“依赖/先后变化”，不能仅凭不同hash或换名认定结构不同。
- 首期保持现有房间逐房推进和明确EXIT；任意房间连接、分支地图、回路、多出口、新谜题机制及无限结构生成不在本阶段范围。
- 有限骨架随机选择仍可能重复，不承诺每次结构唯一或无限不重复；近期避重等策略如需要，须另定明确范围，不默认增加持久存储或公开seed接口。

### 14.3 复用与兼容约束

复用既有生成→严格准入→可解证明→真实规则回放→Store提交→公开状态→存档恢复链。保留1–3房、三难度、谜题/物件/道具数量上限、normal/hard组合资料与依赖深度要求，以及原求解上限；无法证明可解仍不放行，不为增加变化降低校验标准。

当前说明方案实现时，应按实际物件角色、机制、配方、引用和名称生成说明，避免绑定特定房间编号或固定谜题顺序。此处只要求接口便于后续复用，不提前实现多骨架。未来选中的结构实例须同时约束模型精确槽位、组装和验证，不能选一次结构再按另一套结构解释回复。

结构ID/版本与受控验证输入须在证据中可追溯；旧完整定义、hash与存档不重绘、不迁移、不重新调用模型。模型内部合同是否需要升版及公开格式是否受影响，在SD0单列兼容分析，不能默认旧版本继续有效。原Key、账号归属、费用、单次调用及0重试保护保持，不新增供应商或收费行为。

### 14.4 原规划任务与文件归属（实际执行见14.7）

| 任务 | 依赖、Owner与计划路径 | 完成条件 |
| --- | --- | --- |
| SD0 结构设计与验收细化 | 当前方案完成后；Main/Spec：新增docs/structure-diversity-plan.md，维护本计划/SPEC/level_design/DECISIONS | 九组合可行性矩阵、骨架清单、归一签名、变化阈值、版本/旧档政策及精确开工路径冻结 |
| SD1 多骨架选择与合法放置 | SD0；Backend：计划新增backend/app/domain/structure_variants.py及届时生成适配器的最小接入 | 多套结构由明确规则产生；无循环、自锁、不可达必要材料，数量与难度约束保持 |
| SD2 模型合同与说明适配 | SD1；Main/AI负责生成适配，Backend/Spec负责对应内部合同，Frontend仅必要说明文字 | 同一结构贯穿请求/组装/说明，AI参数仍影响真实谜面，既有规则/接口/存档优先复用 |
| SD3 独立验证 | 全部Owner STOP与Main冻结后；QA：计划新增tests/v5/test_structure_variants.py及新review/证据目录 | 结构差异、真实可解回放、发现边界、非法结构拒绝、存档恢复均有来源绑定证据；不以随机hash当多样性证明 |
| SD4 文档与普通同步 | SD3后；Delivery维护README/release，Main维护根进度/Git | 如实披露有限骨架与变化范围，保留失败证据，liy222普通提交推送；发布门另行满足 |

以上路径为后续计划，届时启动前以精确任务卡定案；当前没有相应新实现、测试结果或人员/模型派发。

### 14.5 验收与预算门

1. 同房数、同难度使用受控选择，分别展示至少两套合法骨架；对结构签名、资料分布和可执行先后做独立预期比对，不能仅改文本/答案或排列ID。
2. 每个候选通过原严格检查、可解证明和真实规则动作到EXIT；故意循环依赖、自锁/不可达资料、不足组合深度或越界布局应拒绝/标记尚未证明，不自动修补放行。
3. 在未发现、部分发现、全部发现与跨房阶段核对公开投影和说明，不提前泄露答案，保持服务器最终状态权威。
4. 使用隔离数据库验证当前会话保存/恢复/reload与旧完整定义hash保持；不得使用玩家数据库作测试，不重造旧档或挪用旧验证通过记录。
5. 结构选择、合法性和差异验证先用离线受控输入完成。新模型合同/完整payload费用另做实际纯计量；需要真实模型时仍须新的有限明确批准，失败占次数，异常停止、原账本和0重试保持。
6. 结构可解不等于好玩、每次不同或真人难度合格；有限样本与人类体验分别记录。当前本节为Planned，无新增测试、实际生成、发布tag、main合并或部署结论。


### 14.6 2026-10-27 SD0已细化冻结

当前B实现与必要有限独立验收/提交已完成，按第14节既定顺序进入SD0。稳定细案docs/structure-diversity-plan.md已完成Backend纯元数据核对与独立静态设计读审，九组合均给出F/R两种具体结构；这不是可解证明或产品QA。内容格式2.0.0保持，新结构目录1.0.0单列36合同，旧18与旧完整定义保留。R实际改变机制先后/资料放置/发现条件；有限结构不保证每次唯一。

Main随后可在原已接受范围内明确记录SD1/SD2实施GO，仍须OwnerSTOP、候选冻结、原25000状态/5秒准入、独立SD3与正常liy222提交。当前读审不授予新付费、不允许扩大地图/机制或修改冻结的规则/API/存档体系。设计证据见structure-diversity/design/qa-review.json与sd0-accepted.json。


### 14.7 2026-10-27 有限实施与独立联合验收

SD1/SD2在冻结细案范围内完成：旧F/18合同原样保留，新增R及独立36合同目录；R实际改变机制先后、资料位置和发现门。content仍2.0.0、目录1.0.0；v2仅选择/manifest接入，原编译器、API/Store/AI/预算、存档版本和前端/素材不改。有限随机允许重复，不承诺每次唯一或36种拓扑。

独立SD3的75项唯一执行exit0（含36原25k/5秒证明与领域EXIT、新旧定义/多时刻存档/真实子进程重开、发现边界、40完整payload）；唯一v5 build exit0并绑定98产物。Canvas为联合通过：首轮exit1/290记录中R1桌面/手机已EXIT；仅QA脚本同名出口选择与signal退出认定修正后，R3桌面/手机窄补exit0/301记录，不相加或称一次全绿，正式阶段产品修复0。R1目录8物件按累计槽位与库存验证，不要求8物件同时可见。

36短主题保守上界0.114360—0.161528元；2000四字节3hard四种选择上界0.201504/0.225240/0.201696/0.225432元，均按原0.20元在预留/发送前拒绝，不抬cap。当前无新结构真实模型/叙事质量、生成率或真人难度结论，旧真实435与OPEN保持历史边界；本阶段付费0。证据见review/findings/v5-structure-diversity.md、structure-diversity/qa/result.json与accepted.json。SD4只收尾文档与liy222普通提交/推送，不构成v5发布、tag、main合并、部署或Actions。

## 15. 2026-10-25接受：规则生成物件说明（方案B）

用户明确表示“选择方案b”。接受docs/v5-generation-text-authority-proposal.md中的B方向及TXT0–TXT4；第13节结构选择/typed参数/严格编译/费用等保持，本节优先覆盖物件description来源与模型内部合同版本。选择不等于实现或验收通过，不包含新的付费调用。第14节SD0–SD4继续后置。

### 15.1 职责、合同与禁止行为

内部GenerationContent=2.0.0：root仍为content_version/blueprint_id/title/story/rooms/objects/parameters；rooms精确name/description（氛围），objects精确name-only。版本/蓝图const、原18形状及typed参数严格值域保持。多description/错版本/缺项/extra字段直接拒绝，不能接收后删除、补默认值或退回v1。AI保留故事、氛围、名称与真实数字/排列/映射；名称和背景仍有语义风险，不能承诺全部文案可靠。

Host在合法v2内容的首次声明式组装中生成物件说明：只由Blueprint真实角色/机制/配方/引用与合法名称决定，不接收秘密参数、answers/witness或solver结果。道具与装置名称按actual required_item_id引用；不hardcode obj_key、G1或谜题先后。资料按实际类型描述，不断言字母排序，不提前公开数值、正确顺序或未发现ID。复用原visible_state发现门及规则补充，inspect基础说明本身也须真实，避免两套规则文字重复。当前不新增同义随机化或多骨架。

### 15.2 复用、版本和兼容

新backend/app/domain/generation_content_v2.py提供select_blueprint/content_schema/request_manifest/assemble_draft：旧选择器只调用一次，再只改不可变Blueprint.content_version；v2先严格解析/校验，合格后才创建独立Host内部helper值（合法名称/参数保留，description由Host生成，内部v1 helper tag）调用旧纯结构组装器。它是预先定义的v2到原Draft转换，不能把任何bad v2或模型v1回复作为生产fallback。原回复不改、不伪称Host文字来自模型。

旧blueprints.py、v1 Schema/builder/README原字节保留，旧builder仍可重建。新增generation-content-v2.schema.json/build_generation_content_v2.py/说明，公开API/原Draft/CompiledLevel/规则/Store/存档格式及版本不变。无新持久字段/表/原稿日志；rawhash/合同版本仅在授权隔离验证证据中绑定。旧完整定义与文案/hash不重绘，不通过v2重造旧档或调用模型。

### 15.3 文件归属、依赖与验收

精确Owner/冻结hash/命令范围见evidence/upgrade/v5.0/text-authority-v2/plan.json。Main负责TXT0规格/ADR和AI/v5.py生成prompt及两处合同import；Backend负责TXT1新模块与3新合同文件；QA只准备新v2测试及受替代合同期待的窄调整，不放宽Key、一次调用、预算或未知结果保护；Delivery仅在实际QA后改README/release。compiler/generated.py、API/Store/provider/budget、伙伴函数、素材及旧v1路径冻结。若确有必要影响冻结范围，先明确列出原因与实际影响。

顺序TXT0→接口审读→TXT1/TXT2→所有Owner SOURCE STOP/Main候选冻结→独立TXT3→TXT4正常liy222提交推送。验收覆盖：18精确v2合同及非法拒绝；改名/诱饵道具与四机制三配方、基础extra资料的说明事实；未发现/部分/全部发现边界；生产GenerationService+MockTransport一次请求及原Key/超cap拒绝；新档/旧完整定义的隔离保存恢复reload与hash保持。只选受影响范围，不机械重复无关旧全套/build/UI/付费。

Owner开发检查不等于独立验收；旧失败、旧成功与旧评审原字节保留为各自历史epoch。QA证据输出仅必要计数/布尔/hash或明确合成数据，不读取真实私有定义/投影；失败日志若含临时凭据只本地保留原件并另做显式脱敏公开副本。原单次6000tokens/60秒/0.20元及0重试/原账本/old unknown门保持。当前真实生成和叙事质量尚无v2样本，未来需来源绑定纯预检及新的有限批准；不将离线Mock或代码证明当真实质量通过。

## 16. 2026-10-26：背景操作陈述的有限拒绝修复

最新方案B真实G3技术/Host说明通过，但story要求未实现的“材料归位”（TXT-C6-STORY-01）。本轮执行既有“故事/氛围不得另造操作”约束：AI继续负责故事、氛围、名称与真实参数，content2.0.0字段、Schema/manifest/prompt不变；不由Host接管故事，不承诺全部语义正确，不包含付费调用。

修订1仅扫描story与rooms.description，识别有限的当前请求/义务/离楼前提中，对材料、库存物件或资料的归位/归还/交回/放回/挂回/返还要求。材料别名从已验证的实际item/clue名称与有限通用材料名取得，不绑定钥匙名。否定限本地分句，完成/历史背景及明确失效旧规引述保留，现行告示不能凭引号豁免；后续当前要求仍拒绝。“钥匙不必带走”单句保留为歧义风险，不硬判消耗/丢弃。精确成对例子、归属与冻结范围见evidence/upgrade/v5.0/narrative-guard/plan.json。

入口顺序为原strict_json→exact v2 Schema→有限文字守卫→既定Host helper。命中整份回复拒绝，不改原文/补默认/删句/回退或重试；原完整定义/hash/存档不经新生成守卫重写。名称字段、Host说明、typed参数、结构/规则/API/Store/Key/费用/伙伴/素材冻结。比较可规范化Unicode/空白，接受值不得改写。

任务NG0 Main规格/ADR→NG1 Backend纯守卫及合同说明→OwnerSTOP/Mainfreeze→NG2独立合成专项→NG3文档/liy222普通提交推送。验收为正反成对语句、实际名称关联/字段排除/每房位置、严格入口先后与原文不变、一次合成服务请求错误映射/worker不发布、旧完整定义恢复不运行新守卫；不重复旧18规划矩阵、79套件、浏览器/build或付费。旧真实422与失败文字原样保留为其历史源码结果，不能称为此新源码的真实复测。

有限中文模式仍可能漏报/误报，未知同义、双重否定、跨句关系等不作通用保证。未经新实际样本，不声称有效生成率/任意叙事质量改善，旧OPEN不自动关闭。任何故事职责/字段/白名单语法或语义模型调用变化另行明确决定；当前多骨架仍后置。

## 17. 2026-10-27：重复JSON字段的提示澄清

真实G3被原strict_json以DUPLICATE_KEY首拒，未进入Schema或新叙事guard。本轮只澄清GENERATION_PROMPT：每个JSON对象内键唯一，不同对象可各自含name；一次返回最终完整对象，不拼接修订片段。原严格拒绝、合同、AI职责、调用限制与存档保持，不丢弃重复键或修原稿。不是解析器缺陷修复或新的自由生成能力。

DJ0范围/ADR→DJ1 Main单常量修改及QA准备→稳定候选冻结→DJ2独立现有7节点定向验证和完整请求纯计量→DJ3文档/liy222提交推送。精确文件归属、旧基线与节点见evidence/upgrade/v5.0/duplicate-json-prompt/plan.json。禁止改旧测试、重跑43/79或无关build/UI/评价；使用合成输入和隔离账本，不读取实际私有原稿。

本轮付费0；提示更明确不等于模型遵守、更高成功率或故事质量通过，旧DUPLICATE_KEY失败和OPEN问题保持历史原样。任何后续真实复测需重新绑定来源做预检并取得新的有限批准，本轮不申请或执行。多骨架继续后置。
