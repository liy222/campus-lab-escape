# 结构多样性实施细案

版本1.0 / SD0稳定细案，待独立设计读审 / 2026-10-27。范围来源为用户已接受的《v5正式构建计划》第14节；基线967e812e10c96ecf514798d57f2d346857a0e7e0。当前只细化设计，尚未修改产品、运行新结构证明或正式QA。静态推导与实际执行证据须分开。

## 1. 目标、入口与边界

方案B的实现、有限离线验收和当前G3技术/Host说明单样本已提交；该入口只允许开始SD0，不代表任意故事、真人体验或新结构已通过。现有生成—严格校验—确定性组装—编译证明—规则回放—Store—公开状态—存档链继续使用。

本阶段让相同房数、难度下至少两套结构在资料分布和实际依赖/解谜先后上有差异。保留1—3房、三难度、四机制、每房1—8物件、2—6谜题、最多4道具、normal组合资料、hard组合/深度以及多房跨房依赖要求。保留线性房间推进、回访与显式EXIT；不增加分支地图、环路、新机制、近期避重、公开seed、持久历史、运行时生图或新供应商。有限随机选择允许重复。

## 2. 两套结构的具体规则

F：原始forward结构。物件、资料引用、房间、依赖、槽位与ID保持原字节语义；控制seed0/1仍为position/mapping两族的原结构。

R：reverse结构。反转原PuzzleSlot顺序，再按原来的每房谜题数量依次分配到G1/G2/G3。重新形成单一依赖链：首题无前置，后题只以前一题为前置；对应puzzle物件同步room_id与locked_by。因原末题是item，R的首题为item，钥匙仍在G1且不锁；可正常获得并使用，使用后不消耗。

资料迁移按可信角色/实际引用完成：基础code_source放到其code题的新房间；extra_code/extra_devices的两份资料跟随各自所属谜题的新房间；共享relation与device_source保留G1。relation资料改为首个item题解开后可发现，保证单房也有真实发现条件差异。不能把所需材料放在自己的题目之后或未来未开放房间。物件槽位在各房重新连续编号0—7；先保留非puzzle物件的原相对顺序，再按新解谜链顺序放置puzzle物件。物件身份与引用保持一致，不能用换ID冒充变化。

例：1房easy从code→item变为item→code，relation在item之后可读。3房hard的F为G1(code,sequence)→G2(circuit,extra-code)→G3(extra-sequence,item)；R为G1(item,extra-sequence)→G2(extra-code,circuit)→G3(sequence,code)。R中跨房证据来自G1共享资料被后房题引用；钥匙首题同房不算跨房证据。

## 3. 九组合静态可行性矩阵

下表已由Backend的03761c纯select/内存元数据计算核对，记录见evidence/upgrade/v5.0/structure-diversity/design/backend-assessment.json；仍不是编译/可解证明结果。两资料族采用同一房间/机制结构。

|房数|难度|谜题/各房谜题数|F各房物件数|R各房物件数|组合资料题数|链深度|
|---|---|---|---|---|---|---|
|1|easy|2 / 2|5|5|1|2|
|1|normal|3 / 3|7|7|2|3|
|1|hard|4 / 4|8|8|2|4|
|2|easy|3 / 1,2|5,2|4,3|2|3|
|2|normal|4 / 2,2|6,2|5,3|2|4|
|2|hard|5 / 2,3|6,5|7,4|3|5|
|3|easy|4 / 1,1,2|5,1,2|4,1,3|2|4|
|3|normal|5 / 1,2,2|5,2,4|4,4,3|3|5|
|3|hard|6 / 2,2,2|6,4,4|7,4,3|4|6|

所有R的code/sequence所需资料位于自身房间或G1；首item无需relation，故relation锁首item不形成自锁。此为静态理由，实际仍必须通过原25000状态/5秒求解与真实领域动作回放。任一组合达不到目标须在实施前披露并确认范围，不放宽校验或悄悄排除组合。

## 4. 结构选择与版本兼容

建议内容JSON保持2.0.0：name-only字段、typed参数和值域均不变，只扩展受信蓝图实例目录。新结构目录单独版本1.0.0，不默认为原18变体已经覆盖新结构。

选择索引seed%4：0=F/position，1=F/mapping，2=R/position，3=R/mapping；seed为内部测试控制，继续拒绝bool/负数/非int，不增加公开API参数。生产secrets.randbelow(4)一次选择，再向历史v1选择器传明确family seed，避免二次随机。一个不可变Blueprint实例贯穿messages、schema、manifest、组装与准入。

F使用原blueprint_id；R使用原F ID加`-sv1-reverse`后缀，最长33字符，符合现有Identifier限制。manifest只增加`structure_catalog_version=1.0.0`及各puzzle的`prerequisite_object_slots`（从实际前置题和物件引用派生）；不按ID硬分类，不把证据签名传给模型，也不把这些metadata变成模型输出字段。模型仍必须复制选中schema的blueprint_id const，另一结构的旧回复直接拒绝。

旧blueprints.py、v1和v2的18变体Schema及builder保持原字节；v2 builder通过seed0/1仍能重建原18变体。新增完整36合同目录及独立builder/说明文件。36=9请求×2资料族×2结构，不称36种拓扑；资料族差异不能充当结构多样性。

公开API、Draft/CompiledLevel/rules/policy版本、Store表、完整定义/hash和存档格式不变。完整定义已包含房间/依赖/物件位置，恢复使用已保存定义，不重新选择蓝图、重绘、迁移或调用模型。结构ID和目录版本在请求/Schema/隔离证据可追溯；不新增生产原稿日志、状态字段或数据库表。旧静态18目录是保留的基线子集，新增生产目录须明确列为新来源。

## 5. 归一签名与独立验收

至少分开dependency_signature与placement_signature；full_signature汇合两者。排除AI文案、数值/排列/映射、Blueprint/room/puzzle/object/clue/item的原字符串ID、随机seed与原JSON列表展示顺序。

仅支持本目录的单链：按真实前置边确定唯一拓扑rank；不支持的非唯一拓扑只使签名函数拒绝，不误称原编译器一定拒绝或该图无解。dependency payload保留谜题mechanism/前置rank及材料行，不含物理房间/slot。clue材料行记录kind、真实uses[(puzzle rank, clue_ids中引用位置)]和locked_by ranks；item行记录实际使用题rank与locked_by。这里的引用位置不是AI的positions数组。按整行canonical JSON排序，保留相同/unused decoy行的数量，不需要以原ID为材料重新编号。placement payload另外保存所有物件的kind、uses、room ordinal、实际slot与锁条件，puzzle物件关联其真实rank。full签名汇合两者。排除family/recipe关系族标签，不按原ID打破同构；同一F/R在两族应具有同一归一结构。

独立验证须有：整体一致改名与物件列表重排后签名不变；仅文案/参数变化不变；F/R的依赖与放置两个签名都变化；对同房同难度，实际witness的解题mechanism顺序变化。仅不同definition hash、family名称、物件显示顺序不算通过。

## 6. 精确文件归属与实施顺序（实施前冻结项）

Main：本文、docs/SPEC.md与docs/level_design.md的必要事实增量、正式计划第14节/版本、DECISIONS与根进度、候选冻结/集成/Git。

Backend：新增backend/app/domain/structure_variants.py；generation_content_v2.py仅select_blueprint/request_manifest必要接入，原guard/说明/strict/helper/参数组装保留；新增contracts/v2/build_structure_variants_v1.py、generation-structures-v1.schema.json、generation-structures-v1.README.md。不得改generated.py/compiler/规则、API、Store、provider/budget、AI伙伴、素材或前端。

QA：新增tests/v5/test_structure_variants.py及新结构专项runner/review/证据；现有test_blueprint_generation.py只允许blueprint_for_messages查找从旧18扩展为当前36（使用current_content选择器和seed0—3），保留所有原断言。其余旧测试/原证据不改；旧AST冻结期待属于历史epoch，不冒充当前通过。

Delivery：实际独立验收后README/release与新交付记录。Frontend生产文件预计不改，因当前GeneratedScene已使用room/slot/target_id动态展示；若实际暴露缺陷，再明确新路径和修复范围。

SD0稳定细案读审→Main明确SD1/SD2 GO→Backend/QA各自准备→Owner SOURCE STOP/Main候选冻结→独立SD3→SD4文档与liy222普通提交推送。新源码未稳定不得正式QA，不增加代理或Astra。

## 7. 必要验证和预算

开发阶段可用明确合成数据做有限Owner可解探测，记录为开发证据，不等同独立验收。正式范围需在SD1 GO前冻结：36个选中合同与F/R全矩阵的原编译/动作至EXIT；签名变形与实际机制先后；循环依赖、自锁/未来房材料、组合/深度/槽位越界拒绝；同一结构贯穿一次生产MockTransport、错结构回复拒绝、Key/费用保护；未发现/部分/完整发现；新R与旧完整定义的隔离保存/选定恢复/reload；必要的R浏览器布局/主路径检查。复用旧框架，不重复无关全套或付费。

新manifest下完整请求做纯计量，检查普通主题及2000四字节主题；超原0.20元/6000tokens/60秒上限仍在预占/发送前拒绝，不抬限额。原10元账本/历史3unknown门保留；本阶段无付费授权、真实模型/伙伴/评价调用，未来需要时另做来源绑定提案与新的有限批准。旧真实435此后成为历史源码样本，不能外推新结构实际模型质量。

## 8. 当前状态与剩余判断

当前SD0细案已完成Backend源码/纯元数据核对，待独立稳定设计读审；没有新结构编译/证明/产品QA通过。原B的故事歧义/顺序命名风险仍保留。结构可解、结构不同不代表好玩、每次唯一或真人难度合格。本细案不批准发布tag、main合并、部署或Actions。
