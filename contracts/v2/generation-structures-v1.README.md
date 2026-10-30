# 内部结构目录 1.0.0

2026-10-30：模型请求manifest在每个puzzle中增加与校验词表共源的name_requirements，帮助生成合法后缀与门禁身份名称。只是请求说明元数据，选中Schema、36合同目录、结构与内容版本不变；严格准入保持。

本目录包含9种房数/难度×2资料族×2结构，共36份选中合同；资料族不同不代表拓扑不同。模型内容合同仍为2.0.0，物件只给name，真实typed参数和严格拒绝规则不变。公开API、完整关卡定义、规则和存档格式不变。

内部seed取模4：0/1为原forward position/mapping，保留旧ID与全部结构字段；2/3为reverse position/mapping，ID增加`-sv1-reverse`。生产只随机选择一次，并使同一不可变Blueprint贯穿消息和组装。seed不是公开请求参数，有限选择可能重复。

Reverse反转谜题顺序后，保持原每房谜题数量重新分房并重建单链。item首题与钥匙在首房且不锁，使用不消耗；基础数字源和额外资料跟随实际引用的谜题，共享关系/设备源在首房，关系资料由首item题解锁。每房非谜题保留原相对顺序，再排新链的谜题，槽位连续0—7。是否准入仍由原编译器和25000状态/5秒真实动作证明决定。

manifest仅新增`structure_catalog_version`和各谜题的`prerequisite_object_slots`，后者来自实际前置引用，不按ID判定变体。模型仍须精确匹配选中Schema的blueprint_id，不接受另一结构的回复，不修补或重试。

`structure_variants.canonical_structure`仅支持唯一单链，返回schema_version、dependency和placement。谜题以真实依赖拓扑rank归一；材料行记录kind、实际uses和锁条件，整行排序保留unused decoy及重数；placement另含room ordinal/slot/puzzle_rank。排除字符串ID、family/recipe族标签、文案、参数和展示列表顺序。`structure_signatures`返回dependency/placement/full三个SHA256。不支持的图或引用以`ValueError('STRUCTURE_SIGNATURE_UNSUPPORTED')`拒绝签名，不表示编译器已经判断无解。

显式重建和只读核对：

```powershell
python contracts/v2/build_structure_variants_v1.py
python contracts/v2/build_structure_variants_v1.py --check
```

历史v1/v2的18份合同与builder保持原文件；旧v2 builder用seed0/1可精确重建其基线子集。本36份目录是新增来源。结构变化不证明任意AI文案正确、真人难度或每次生成唯一；没有新增模型调用授权。
