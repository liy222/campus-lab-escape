# SP-01 Backend 开发记录

2026-10-29，代码基线b09908b。普通功能实现已完成，Backend source STOP，待集中独立复核和真人检查。本文是Owner开发记录，不是独立QA或真人接受。

## 已完成

- 新增`backend/app/domain/puzzle_purpose.py`：按真实前置祖先找每房覆盖全部本房任务的唯一末题，生成passage_control、目的房间、真实art载体；其余为puzzle_control。资料/物品释放只按同房实际锁引用及已蕴含前置判定，不新增柜体动作。
- `generation_content_v2.py`：manifest新增每题effect；原严格JSON、exact Schema、叙事检查之后校验名称；合格原名不改写。Host说明增加真实通行效果；非法回复不进入完整Draft helper，不补写、不重试。
- `AI/v5.py`仅补生成prompt的用途/载体命名职责。`generation_observability.py`仅SOURCE_FILES加新helper，其他采集语义不变。内部content2 README仅追加本轮说明；Schema、版本、物件数量、机械结构与art_id不变。
- 收尾按Main要求补同一空间语义提示：rooms.name表示可进入的房间/区域，不将柜、锁、桌面当独立房间。不增加房间名正则，不改旧名称；此最终prompt交QA做完整payload纯计量，没有重跑上述开发组。
- 旧完整定义的加载不调用新名称校验，不迁移或重写旧定义、Hash、档案或玩家数据。

## 接口

`puzzle_effects(blueprint) -> dict[object_slot, effect]`。每effect有purpose（passage_control或puzzle_control）、carrier（实际terminal或circuit）、unlocks_material_slots；门禁另有destination_room_slot（下一房间槽位或EXIT）。不支持的Host结构抛`BLUEPRINT_PURPOSE_UNSUPPORTED`。

`validate_puzzle_names(blueprint, names, effects) -> None`。有限名词准入：terminal主体为终端、控制台、控制器、控制面板、验证面板、操作面板、读卡器；circuit主体为供电箱、配电箱、电源箱、线路箱、电路箱、控制箱。门禁另须门禁/门锁/通行/出入口身份。柜体功能身份拒绝，明确位置修饰“柜旁门禁终端”“储物柜门旁的门禁终端”保留。错误纯code为`GENERATION_PUZZLE_NAME_INVALID`，沿既有narrative诊断。

`describe_effect(effect, room_names) -> str`不接参数、答案或witness。目的房间名称属于原exits公开的下一目的地；不列未发现资料ID、具体内容或答案。最简合法门禁名：code/sequence/item用“门禁终端”，circuit用“门禁供电箱”；普通装置可用“校验终端”“线路供电箱”。

## 实际检查

Python均为`C:\Users\liyh\.conda\envs\1\python.exe`。

- 只读核对：2c37d5、d225dd、2e4163、99eed3均exit0；没有导入应用、访问密钥/活账本/玩家库或旧私有原稿。
- `python evidence/project/stages/v5-passage-semantics/automated/backend_development.py`，73ee0a exit0，外层2.3437002秒，内部1.574564秒，首败null。36组合仅pure metadata与名称检查，没有36次proof；含真实引用改名、tuple重排、四机制门禁覆盖、8个有限名字例、普通假柜拒绝、strict/schema先于名字校验、坏raw不变/helper不调用。
- 同一有限开发命令已实际完成F/position seed0和R/mapping seed3两份3房hard原编译证明，各33领域动作至EXIT，每房门禁完成前出口false、完成后true；原25000状态/5秒限制不动。另以旧柜锁名字构造合成旧完整定义，调用实际V5Database.load_compiled于仅有内存cache的对象（未调用数据库构造），确认Hash/完整定义不变。此旧加载另有一次原proof，原合成旧定义构建为prove=False。
- 同命令中生产GenerationService使用一次本地假Provider回复用途冲突名称，实际拒绝MODEL_INVALID_OUTPUT/narrative，假回复1次、重试0、真实Provider0。三个原builder的`--check`均exit0：v1内容18、v2内容18、新结构36。上述有限组已实际执行，后续不重复或扩展Owner测试。
- 静态初查e727aa exit1：检查器直接比较Windows CRLF文件与Git LF blob，首个generated.py产生假差异；7d1ef9 exit0确认444个CRLF对0个、LF归一后完全一致。只改比较方式，没有产品修复。修正静态检查完成后结果见`automated/backend-static-check.json`：语法通过；AI除GENERATION_PROMPT、观测helper除SOURCE_FILES外AST不变；原规则、blueprints、结构、Store、provider/budget与三份Schema内容未变。
- 修正静态命令b4d074实际exit0（0.6004903秒）；之后仅GENERATION_PROMPT补上述房间/区域一句，未扩大功能验证。
- 开发控制台中文受终端编码显示为替换字符；结果文件以UTF-8写入，未改写为控制台乱码。完整合成结果为`automated/backend-development-result.json`，可复现脚本同目录。

## 限制与交接

有限词法不保证任意AI中文语义，可能拒绝未列别称或漏过复杂复合名称；没有真实模型遵循率/有效生成率或真人难度结论。未运行build、浏览器、全后端套件、HTTP存档流程或付费。现有旧关卡仍保留原故事/名称/说明；本修复只影响新生成内容。用户此前认可画风和选择方向不等于本阶段接受。

QA接集中必要复核，Main整合前端出口锁态并提供实际预览。请用户本人以新生成关卡检查“门禁开放通道、普通装置不冒充柜锁”、锁定/可通行按钮与场景名称/画面一致性；当前为待真人检查。
