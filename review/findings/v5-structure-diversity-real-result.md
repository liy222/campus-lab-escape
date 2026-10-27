# Reverse G3：单样本技术及Host说明有限通过

独立AI QA智能体复核：唯一批准调用`8a5ac3` exit0（6.676秒），新reverse G3严格准入ready，14个name-only槽位及四额外资料齐全，经33次实际HTTP动作到EXIT，6谜题/7线索。定义hash为`5371808d6549df60336bff859b89556649822465a902716427bff7ff3a33e948`。真实解题机制序为item→sequence→code→circuit→sequence→code，与当前反向结构一致；这不证明普遍生成质量或有效率。

本地审计是**联合完成，非单次全绿**：首helper`ff58e3` exit1。其源码194—197行的最终投影、道具保留、实际机制序及relation门断言，和之前初始＋33步状态hash，均先于199行accounting阶段；输出已到此阶段，后在242行读取不存在的`recorded_utc`时报KeyError。实际授权字段为`approved_utc`。原helper/sourcehash、失败输出checkpoint保留，授权/marker等原件未改。窄tail`6b542d` exit0只补账目顺序和闭合文案，derive/compile/solve/apply_action均禁止，未重复33回放。

Host全名配对、钥匙不消耗并保留、G1 relation在首item前隐藏/后可见，按首审已完成断言有限通过。保存witness引用时序抽取为未观察8/部分0/完整22，**不是第二次规则回放，也无本样本实际部分发现覆盖**。原完整HTTP响应未留正文，opaque bodyhash无法重构；状态hash比较重用记录的session/level/generation/时钟/save元数据，仅说明保存状态链一致。自动elapsed0秒/S不代表真人难度；本真实样本未做save/restore。

仅读取严格hash/shape门后的显式玩家文案衍生版：故事为逐室核对，未见明确要求归还材料、强制整理或虚构资料袋。钥匙完整名称与锁扣Host引用一致；Host设备/数字资料明确符号源序，没有字母排序说法。四份资料名“前段/后段”仍有顺序提示风险，不武断判发现门失效或答案泄漏；不接受任意文案语义，历史OPEN不自动关闭。

实际批准`call_94350e33f3094a8abf7c84b2cf5549b1 item0`绑定预览/455来源/唯一scope，approved_utc早于marker和dispatch，journal一组闭合，current455匹配，finalization为空。输入3067、输出503、cachehit384，冻结费率复算usage上界**0.00940536元**，预占0.162584元；保存账本149→150，charged upper units1142225520→1151630880。旧unknown3身份同、新unknown0、pending0、frozenfalse。非账单；唯一授权已耗尽，无重试/伙伴/评价。

provider＋定义/witness/replay四原件只作本地机器输入，原字节不修补/移动，精确ignore；公开封存只绑定其hash，元数据/文案是明确衍生版。公开有限凭据/字段扫描0命中，非任意编码保证。预检8及旧QA102原件保持。QA未读旧私有body/真实Key/config/实时账本/玩家DB，无新HTTP、模型、证明、tests/build/UI、付费或产品修改；准确命令/exit/hash见最终JSON。SOURCE STOP。
