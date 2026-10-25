# 单 G3 槽位完整性复测提案：独立 AI QA 预检

2026-10-25。**有限离线预检通过，仅为待新授权的单次提案。** 执行者为独立 AI QA 智能体，无真人或教师审查、试玩或签字。没有新模型调用或叙事质量通过结论。

新 runner SHA256 `0f6bc53c52d3cb987f4e2047a3f312a4fd900aaa286a20c8e97dcab0466de554`；仅六处获准命名/路径字面量变化，逆替换整份字节等于旧 `eed8325b…`，归一 AST 相同。原授权先于 marker/config/Key/ledger、单次 journal、固定历史三条 unknown 身份、来源/费用/模型/凭据异常停止及最终 source/safe-ledger 门均继承。复用旧已封存 26 授权、5 finally 与 5 scope 负例证据，没有重复探针。旧预检 8/12 封存内容逐项匹配。作者首次 `fec78a` exit1 是落盘前静态比较器未处理路径子串，作者窄修 `65cd05` exit0；原记录保留，不是产品或保护逻辑失败。

Main 仅一次 `python -B -X utf8 evidence/upgrade/v5.0/blueprint-slot-completeness/real-samples/run.py --prepare`（`6f77e6`，exit0）。QA 未运行 prepare/execute。实际预览 SHA256 `ba61fe1ff55d1d8cd03140df7ca9d38b60227372565e25beaf6313d10ed54179`，绑定当前产品410、候选原字节及新 runner，共412来源，bundle `279c04228d1217c6c25e1c0381eea0646d8e9982f301f8972ab6317fbb659a6b`；当前逐文件哈希全部匹配。完整来源表仅保留在 Main 预览。

唯一 G3 与旧实际使用相同主题、三房/hard/mapping_v1、受控 Host seed1，无公开 seed API。完整请求11148 UTF-8字节，body SHA256 `8237c17e07e0b79cfd9e9707cfd2e71687d2ba0b7086d7fcf86a2c70f88f653e`，保守输入52784、输出6000 tokens/60秒，上界 **0.153568元**；拟议最多1次/0.20元，零重试/伙伴/evaluator。这是未发送请求的费用上界，不是账单或授权。

实际 body 与旧离线 G3 请求仅 system prompt 更新；当前 prompt 字面量匹配冻结源码。Schema 仍要求14个 exact物件槽，包含四个额外资料物件；extra参数数组不替代这些 name/description。item_use 指向同一 manifest 的 kind=item 槽 obj_key、use_item、consumed=false。提示保留完整同名引用、使用后保留、不虚构物品/归还/额外清单的意图，但不保证模型遵守。未来实际复核须区分四槽完整性、原准入/可玩回放、完整钥匙名称与非消耗语义、无虚构必需资料袋/归还清单、设备/符号次序的有限文本观察，不能从技术成功外推真人体验或任意主题可靠性。

预检时 user-authorization.json、execute-started.json、dispatch-journal.jsonl、raw-sensitive/ 全不存在。未来三份 private定义/witness/replay 精确路径经原通用 ignore 匹配（git check-ignore exit0），只能本地保存，不发布或输入模型；目前没有这些证明。Main 须先正常同步并取得新的有限明确批准，绑定本次预览/来源/单次上限，才可进入执行入口；当前 ledger 状态未由 QA 读取，未来只能在获准执行内核对。

QA 实际只读命令：`205b32`、`a7de07`、`1e1354`（计划/源码/旧证据）、`58afd7`（独立逆字节/AST/旧 seal 与来源核对）、`87031b`（实际预览）、`4962f9`（原计价与旧限制）均exit0；末次标准库只读预览/费用/忽略核对及新metadata封存同样exit0，完整命令在工具记录与 preflight-preview-v1.json。没有导入runner/provider，未访问配置/Key/当前ledger/DB/network，paid0；不重复产品测试、HTTP、编译/规划/witness、build/UI/eval。

旧失败原稿、拒绝/费用事实和 BP-REAL-NARRATIVE-01 OPEN 不变；本轮只新增本报告及新namespace preflight-*.json。新预检 **SOURCE STOP**，不提交、不推送、不派发。
