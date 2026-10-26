# Content2 单 G3 实际复测提案：独立 AI QA 预检

2026-10-26。**有限离线预检通过，仅可作为待新授权的单次提案。** 复核者为独立 AI QA 智能体，无真人/教师试玩或签字；当前没有v2真实模型输出、准入或文案质量结论。

新runner `5103629ab3ea01411def15068d08b8bbb3480d65a11437cba1547dca40aa05b7` 只作11项获准替换：来源410→420、两处选择器import切v2及命名/候选元数据。逆替换整份字节与旧0f6bc53c一致，归一AST及保护逻辑保持；实际GenerationService仍单次选择同一v2骨架并贯穿消息/组装。复用旧封存保护证据，不重复probe、79套件或真实执行。

Main仅一次 `python -B -X utf8 evidence/upgrade/v5.0/text-authority-v2/real-samples/run.py --prepare`，`7eee98` exit0。QA初审 `e5b2d6` exit0，新预览读审 `668a09` exit0，末次标准库来源/费用/Schema/ignore/absence与封存命令exit0；没有导入runner或重复prepare。

实际预览SHA256 `6f7d48de595192dc9a4b106a07349bbf18121372503a80c1b362f35145fe41f2`。420候选输入加候选原字节与新runner，共422项，bundle `dc06818ccf9031d4590d6266fd217cbd87ac6bb25a21bd3e03ad1dde923bf085`，当前逐文件全部匹配；唯一完整来源表在预览。

精确提案为原同主题G3、三房/hard/mapping_v1、内部受控seed1，最多1次/0.20元、0重试/伙伴/evaluator。完整body11728 UTF-8字节，SHA256 `ec708c41b517c7d601e10e106bbc27ef4637fa53d23bf3f9a371b6b14565919a`，保守输入55104、输出6000 tokens/60秒，发送前费用上界 **0.158208元**，不等于账单或收费授权。

实际请求Schema恰为选定content_version2.0.0变体：14个objects槽只准name、拒额外description，包含四个额外资料物件；rooms保留name/description，typed参数与原结构不扩展。manifest仍有真实道具槽的use_item/consumed=false，system prompt匹配当前冻结源码。严格v2通过后才由Host构造说明，不接收旧v1或丢弃坏字段；这只是已审实现路径，不能推断模型实际遵守。

固定历史三条unknown身份、10元总cap、fresh授权先于marker/config/Key/ledger、独占marker/journal、profile/source/payload/secret/model/并发和最终source/safeledger停止门继承。本轮不打开实时账本；未来只能在新实际批准后由执行入口检查。授权文件、marker、journal、result/provider/ledger输出和raw-sensitive目录均不存在。未来三份私有证明路径仍被原通用ignore覆盖，只可本地保存。

当前无付费许可；Main须先正常同步并取得新的明确最多1次/0.20元批准，绑定本次来源及预览后才可执行，失败也占名额。未来AI QA只按显式allowlist读取必要的虚构玩家公开故事/氛围/名称/Host基础说明，其余只输出计数/布尔/hash，禁止参数、线索值、答案、witness或私有投影进入工具/AI上下文；不能靠宽泛metadata dump提取文案。

原失败/成功及其费用、旧OPEN叙述finding均保留。名称/故事/氛围仍可能误导，未来一个样本也不能证明普遍质量或真人难度。本轮无旧实际raw/私有正文、Key/config/currentledger/玩家DB、provider/网络/付费访问，无产品测试/build/UI/eval。新报告与preflight JSON SOURCE STOP，不提交、不推送、不执行收费脚本。
