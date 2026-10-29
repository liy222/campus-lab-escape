# GenerationContent 2.0.0（模型内部合同）

2026-10-29通行语义补充（新生成入口）：`puzzle_purpose.py`按真实前置祖先，找出覆盖本房其余任务的唯一末题，标为`passage_control`；manifest的各puzzle增加Host确定的`effect`，包含用途、实际`carrier`、真实可释放的本房资料/物品槽位，门禁另含目的房间槽位或EXIT。其余题为`puzzle_control`，当前不新增柜体、钥匙获取步骤或机制。Host基础说明补充真实通行效果，不显示答案、参数或未发现的资料ID。

新名称在原strict JSON、exact Schema和叙事政策之后、完整Draft构造前接受有限校验：谜题名称须以实际terminal/circuit载体支持的明确名词为主体；门禁题还须明确门禁、门锁或通行身份。柜锁/柜体身份拒绝，明确位置修饰如“柜旁门禁终端”可保留。错误为纯code `GENERATION_PUZZLE_NAME_INVALID`，沿现有narrative诊断；合法模型原名不改写，不修补、不重试。此有限名词规则不是任意语义保证，可能拒绝未列出的合法别称或漏过复杂歧义。内容JSON的字段、2.0.0版本和原Schema字节不变；旧完整定义/Hash/存档加载不运行新名称校验，不迁移玩家数据。

用户选择B：AI保留标题、故事、房间氛围、房间/物件名称和真实谜面参数；Host提供物件说明。删除必填的objects.description属于破坏性变化，因此使用新的内部2.0.0合同。此合同不是新的HTTP接口，不改变原Draft、CompiledLevel、规则或存档格式。

生产适配模块为`backend/app/domain/generation_content_v2.py`。四个纯接口是`select_blueprint`、`content_schema`、`request_manifest`、`assemble_draft`。选择器只调用一次历史纯选择器，再为原不可变Blueprint设置content_version=2.0.0；position_v1/mapping_v1仍是原结构族名称。原两族、九种请求形状、18合同变体和前向结构不变，不包含后续结构多样化阶段。

调用方须让同一个选定Blueprint贯穿消息与组装。根字段严格为content_version、blueprint_id、title、story、rooms、objects、parameters。content_version为2.0.0；blueprint_id复制所选Schema的const。标题/故事保留原40/240字符限制；rooms精确填齐所选槽位，每项仍为name、description。objects也须精确填齐，但每项**只能有name**，非空且最多40字符。模型若输出objects.description、额外键、缺项、旧版本或非法参数，直接拒绝，不接收后丢弃。

typed参数和值域与历史v1相同：position族的单数字字符串、整数位置排列和设备排列；mapping族的符号排列与数字/设备对应关系；较大形状的extra_digits/extra_devices仍是独立四项参数，按原合同拆成两份资料。没有默认值、模型重试、旧关卡回退或测试fixture。

`assemble_draft`先对原始回复运行原strict_json保护（64KiB、深度32、重复键、非有限数、不安全文本）及严格v2校验。只有合格v2才构造一个独立的Host内部helper值：保留已接受名称、房间、故事和参数，为物件加入确定性description，使用历史纯组装器要求的内部v1格式标签。这个标签只服务于复用冻结的结构组装函数，不接受模型v1回复，也不是把非法v2交给v1补写。原raw不被修改；错误不会触发降级。原worker继续执行同一编译、证明和Store提交链，组装器内部不重复运行proof。

在严格JSON和exact Schema通过后、helper构造前，增加独立修订`NARRATIVE_GUARD_REVISION='1'`的有限叙事拒绝政策。只扫描story和每间房的description；标题、房间名、物件名、Host说明及参数不作为待扫描文案。目标限材料、物品、道具、钥匙、资料、记录卡、器材、标本、样本、文件、卡片，以及本次实际item/clue的合法名称；动态名称只作escaped literal匹配。

政策只识别短子句内针对这些目标的明确要求/义务/离开前提，动作限归位、归还、交回、放回、挂回、返还。命中直接抛纯code `UNSUPPORTED_NARRATIVE_OPERATION`，不回显句子、不删改raw、不重试。比较使用NFKC并合并格式空白（含换行），但不写回内容；真正标点与转折仍用于局部分句。本修订识别的局部否定、已完成/历史表述及明确作废的旧引语不作为当前要求；作废范围仅覆盖相应旧引语，后面的当前要求仍检查。引号本身不豁免当前通知。

例如“所有材料都要归位”属于未实现操作；“器材已经归位”“无需归还材料”保留。“钥匙也不必带走”存在结束后离楼的解释空间，不在此硬拒绝子集中。此有限匹配不是通用语言理解：陌生措辞、复杂引述、双重否定、跨句关联和动作同义词可能误报或漏报；没有测量普遍误报率或实际生成有效率。政策不把故事改为Host模板，不新增字段、持久元数据或版本迁移，content_version仍为2.0.0。拒绝也可能降低有效生成率，未来获批调用仍会消耗名额，不能自动补发。

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
