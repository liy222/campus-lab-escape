# 槽位完整性单 G3：独立 AI QA 实际结果

2026-10-25。**本次有限技术检查通过，叙述质量仍未通过，原 BP-REAL-NARRATIVE-01 保持 OPEN。** 复核者为独立 AI QA 智能体，没有真人或教师试玩、签字或难度验收。

Main 唯一执行 `python -B -X utf8 evidence/upgrade/v5.0/blueprint-slot-completeness/real-samples/run.py --execute`：记录 `c122f1`，exit0，9.37秒，无重试。实际 G3（三房/hard/mapping_v1、受控 Host seed1、原同主题）ready_and_replayed，33次实际 HTTP 动作到 EXIT，6/6谜题、7/7资料。原缺四槽的失败原稿及其 exit1 保留，不能改写为本轮成功；本轮也不证明提示改动必然导致成功。

实际原稿严格解析/内部 Schema 零错误，14个 exact物件齐全，含四个额外资料物件。纯离线 assemble 的 Draft 与本地保存定义相同；从该 Draft、原 derive 和已保存 witness 重建 CompiledLevel，定义/witness哈希一致。未调用 compile_level 或 solver。使用原纯规则解释既有33动作：initial、33/33逐步状态哈希及最终完整投影全部匹配；use_item 前后背包相同、consumed_item_ids为空，所需钥匙保留到 EXIT。没有重发 HTTP、重新生成关卡或运行测试。逐步完整 API body 未保存，仅有 opaque api_result_sha256，无法独立重构含随机事件标识的响应体哈希；这里确认的是保存状态链与动作语义。

实际批准引用 call_a4be3eac419849f480b0e432f9b62c7e item0（最多1次/0.20元）与预览、marker及两行 before/after journal 绑定。发送 body 完全等于已审预览，11148字节，上界0.153568元。预览 SHA256 `ba61fe1ff55d1d8cd03140df7ca9d38b60227372565e25beaf6313d10ed54179`；412来源 bundle `279c04228d1217c6c25e1c0381eea0646d8e9982f301f8972ab6317fbb659a6b`，实际source_after及当前逐文件均一致，完整来源表只保留预览。

供应商记录 requested/reported deepseek-flash、finish=stop；prompt2806、completion817、cache_hit0。usage上界及已保存账本差额均为 **0.012148元**：calls145→146，charged1103688000→1115836000 units。历史3unknown身份不变、pending0、frozenfalse、finalization_failures空；QA只读保存快照，没有打开实时账本。批准名额已全部使用，剩余0，不能补发。自动回放 elapsed_seconds=0、rating=S 只是程序结算，不是人类时间/体验证明；本轮未测 save/restore。

文本有限观察：

- 最终道具装置明确完整引用“标本柜钥匙”，写使用后保留；没有虚构“标本资料袋”。这只支持本样本局部改善。钥匙物件自己的原文仍说“用后照常挂回原处”，而真实工具没有归还动作、规则保留背包；该句引入未实现操作预期，与最终装置保留说明存在叙述冲突，不能宣布旧finding全面关闭。
- 设备说明为“挂牌上按字母排着设备简称，顺序提示与对照卡上的符号对应”。实际该 source 资料显示的是符号源序，非设备简称；source_symbols_not_alpha=true，mapped_devices_alpha=true。映射后设备恰好字母序，因此不能无条件判原句所有解释均为假。排序主体/材料类型混淆构成歧义与误导风险，未通过完整语义检查；没有据此认定原规则不可解。具体序列/答案不进入公开报告。

QA 实际命令均 exit0：`bdb0d6`、`d4fe5b`（保存原件读审），`99c39f`、`3ebfb9`、`9dc8e6`（纯规则源码），`c22350`（严格组装与33步内存核对），`61fc69`、`d24d68`（旧封存字段读取），`2cca33`（来源/批准/费用/历史seal与有限隐私检查）；命令为 PowerShell只读或 `C:\Users\liyh\.conda\envs\1\python.exe -B -X utf8 -`，完整范围见对应 qa-actual JSON及工具记录。末次新报告/哈希seal写入命令exit0；QA未重跑Main执行器。

旧QA63/16/9、预检12/8/本轮8、历史actual17+local6及最近失败14的封存哈希均保持，53注册源码仍匹配。三份本轮私有定义/witness/replay仅本地保存，公开seal只绑定路径/hash，不发布正文。十份公开原输出有限token/cookie/bearer模式检查零匹配；未读取配置Key，不能据此证明所有可能格式均无敏感值。

读取失误须保留说明：`d4fe5b` 的 metadata过滤过宽，私有clue投影曾进入本地工具记录及 AI QA上下文。没有写进公开证据/仓库，也未发送生成/伙伴/评价provider请求；不能声称“从未进入任何模型上下文”。后续私有读取仅输出必要计数/布尔/hash，受影响本地工具输出不得公开。原私有文件不改。

新增仅本报告与新namespace qa-actual-*.json，SOURCE STOP。没有新付费、provider/config/Key/liveledger/DB访问，没有新测试、HTTP、编译搜索、build/UI/eval；不推断普遍成功率、任意主题可靠性或真人体验，不作产品修复或新增付费提案。
