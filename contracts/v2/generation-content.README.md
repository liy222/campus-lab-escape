# GenerationContent 1.0.0（模型内部合同）

2026-10-24，用户接受Host结构+AI内容/谜面参数。此合同不是新增HTTP接口；20个公开v2路由与`level-draft.schema.json`不变。模型回复不再直接充当完整Draft。

Host每次只选择一个不可变Blueprint。`select_blueprint(room_count, difficulty, seed=None)`由服务端随机选择position_v1或mapping_v1；内部非负整数seed可确定族，公开生成请求没有seed/family字段。两个资料结构族覆盖九种房数/难度，共18个合同变体，采用前向依赖链，不是18种不同拓扑。

`content_schema(blueprint)`返回该次选择的精确Schema，`request_manifest(blueprint)`只说明槽位、角色与参数含义；不提供CompiledLevel答案/witness。`GenerationService`将相同Blueprint用于消息和严格组装，保留旧worker的`draft_schema`调用参数但不向模型发送原Draft Schema，也不修改调用者的Schema。

道具装置的manifest另含`item_use`：`item_object_slot`从该谜题的实际`required_item_id`找到对应物件槽位，`tool`为`use_item`、`consumed`为`false`。模型叙述须引用本次回复中该槽位的同一物件名称，描述使用后保留，不虚构另一件必需物品、放回或额外操作。它只补充已有规则关系的输入，不改变模型输出Schema、组装或游戏规则，也不能保证模型叙述完全正确。真实样本中“资料袋/钥匙”的错误原稿和准入结果保持；补充后的叙述效果尚未真实复测。

模型根字段必须恰为：

| 字段 | 约束 |
| --- | --- |
| content_version / blueprint_id | 复制当前Schema的const |
| title / story | 非空文本，最多40 / 240字符；仍受原安全文本及答案入叙事检查 |
| rooms / objects | 精确已选槽位ID；每项只有name、description，最多40 / 240字符 |
| parameters | 只含当前变体要求的键和类型 |

position_v1使用四个单数字字符串`digits`、1–4完整整数排列`positions`；有基础sequence时还使用四设备完整排列`devices`。mapping_v1使用A–D排列`code_symbols`及单数字`digit_map`；有基础sequence时另使用E–H排列`sequence_symbols`及互异设备`device_map`。设备固定白名单为device_a–device_d。5题时需要独立`extra_digits`，6题还需要独立`extra_devices`，各按合同拆成前2项/后2项两份concat资料。数字可重复，排列不可重复，整数不得用float/bool冒充。

`assemble_draft(blueprint, raw_model_content)`先使用原`strict_json`的64KiB、深度32、重复键/非有限数/不安全文本保护，再严格校验Schema、exact槽位和typed值；全部通过才按声明规则构造完整原Draft。此转换不是对坏回复的补写/改值。任何缺失、额外字段、错族、错排列或非法内容直接拒绝；生产不调用`make_fixture`、不补默认内容、不回退历史关卡，也不重试模型。

完整Draft继续由原编译器执行引用、配方、规模、依赖、布局与25000状态/5秒证明及witness回放；原Store只提交已准入定义。文案泄露答案仍拒绝，不在组装阶段删改文本。reset/restore读保存的完整定义和原hash，不重新生成蓝图或调用模型，旧定义/档案格式不改。

静态[Schema](generation-content.schema.json)以oneOf收录18个精确变体；实际请求只发送已选变体。显式重建与一致性检查：

```powershell
& 'C:\Users\liyh\.conda\envs\1\python.exe' -B contracts/v2/build_generation_content.py
& 'C:\Users\liyh\.conda\envs\1\python.exe' -B contracts/v2/build_generation_content.py --check
```

Schema和局部证明不是独立QA或真实模型质量证明。一次调用、原GenerationLimits与Key/费用/任务边界不变；没有新增付费授权。验收与实际结果另见正式计划第13节及本轮来源绑定证据。旧53-source评价登记不包括这条新路径，不能用其有限Claim替代本次验证。
