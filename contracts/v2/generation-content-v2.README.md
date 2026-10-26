# GenerationContent 2.0.0（模型内部合同）

用户选择B：AI保留标题、故事、房间氛围、房间/物件名称和真实谜面参数；Host提供物件说明。删除必填的objects.description属于破坏性变化，因此使用新的内部2.0.0合同。此合同不是新的HTTP接口，不改变原Draft、CompiledLevel、规则或存档格式。

生产适配模块为`backend/app/domain/generation_content_v2.py`。四个纯接口是`select_blueprint`、`content_schema`、`request_manifest`、`assemble_draft`。选择器只调用一次历史纯选择器，再为原不可变Blueprint设置content_version=2.0.0；position_v1/mapping_v1仍是原结构族名称。原两族、九种请求形状、18合同变体和前向结构不变，不包含后续结构多样化阶段。

调用方须让同一个选定Blueprint贯穿消息与组装。根字段严格为content_version、blueprint_id、title、story、rooms、objects、parameters。content_version为2.0.0；blueprint_id复制所选Schema的const。标题/故事保留原40/240字符限制；rooms精确填齐所选槽位，每项仍为name、description。objects也须精确填齐，但每项**只能有name**，非空且最多40字符。模型若输出objects.description、额外键、缺项、旧版本或非法参数，直接拒绝，不接收后丢弃。

typed参数和值域与历史v1相同：position族的单数字字符串、整数位置排列和设备排列；mapping族的符号排列与数字/设备对应关系；较大形状的extra_digits/extra_devices仍是独立四项参数，按原合同拆成两份资料。没有默认值、模型重试、旧关卡回退或测试fixture。

`assemble_draft`先对原始回复运行原strict_json保护（64KiB、深度32、重复键、非有限数、不安全文本）及严格v2校验。只有合格v2才构造一个独立的Host内部helper值：保留已接受名称、房间、故事和参数，为物件加入确定性description，使用历史纯组装器要求的内部v1格式标签。这个标签只服务于复用冻结的结构组装函数，不接受模型v1回复，也不是把非法v2交给v1补写。原raw不被修改；错误不会触发降级。原worker继续执行同一编译、证明和Store提交链，组装器内部不重复运行proof。

Host基础说明只读取可信角色、机制、配方、实际引用和合格名称，不接收parameters、answers、witness或solver输入：

- 道具说明拿入背包及使用后保留；道具装置从required_item_id解析真实item对象，再引用其名称，不依赖固定obj_key、房间或排列顺序。
- 数字/设备源与映射符号源明确区分；位置表、符号对应表、数字/设备片段按真实角色标明类型，不假称字母排序，不提前声明片段组合次序。
- 四机制装置的基础说明简短真实；沿用GeneratedRules.visible_state已有的配方、线路及不消耗规则补充，避免重复整段指令。inspect返回的基础说明本身也真实。

模板不读取或插入秘密参数值、完整密码、正确设备序或未发现的clue ID；引用名称仍须经过原安全与答案入文案准入检查。具体资料事实和组合次序继续通过原观察/发现门展示；不修改GeneratedRules。模板确定，不增加随机同义文案。

历史[GenerationContent 1.0.0](generation-content.README.md)、Schema及构建器保持原字节和可复现入口。已保存完整定义中的旧文案、hash和档案不重绘、不迁移；恢复无需新模型合同。新关卡因新说明产生自己的定义hash。原始模型回复哈希与内部合同版本只在授权验证证据中分别绑定，不新增产品持久字段、原稿日志或数据库表。

显式构建与只读检查：

```powershell
& 'C:\Users\liyh\.conda\envs\1\python.exe' -B contracts/v2/build_generation_content_v2.py
& 'C:\Users\liyh\.conda\envs\1\python.exe' -B contracts/v2/build_generation_content_v2.py --check
& 'C:\Users\liyh\.conda\envs\1\python.exe' -B contracts/v2/build_generation_content.py --check
```

Schema、确定性说明和合成检查不能证明任意AI语义正确。名称、故事、房间氛围仍可能误导，模板也会重复；安全与答案入文案检查继续由原编译器判定。旧真实样本及OPEN finding保留，新合同不追溯修复历史文案，不代表已真实验证质量，无新增付费授权。
