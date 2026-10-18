# 真实AI伙伴试玩：独立审查协议

首批真实结果审查结论：**不能判整批质量通过，需窄修场景范围与引用策略**。Main实际执行7次真实调用和1次本地对照；本QA仅读记录、不发付费请求、不读凭据或canonical预算数据库、不改产品。

## 首批实际结果

Main结果：`evidence/integration/ai-companion-real/20261018T110144068872Z-real/result.json`。QA命令 `C:\Users\liyh\.conda\envs\1\python.exe -B -X utf8 tests/ai-companion-real/review_result.py evidence/integration/ai-companion-real/20261018T110144068872Z-real/result.json`，exit0；279项文件hash/算术/对照核对，issues[]。这只表示执行记录一致，不代表语义质量全通过。

7次真实调用账本计费上界0.016716元（依据实际usage、既有峰值价格账本，非供应商账单）；累计0.87425848→0.89097448元，原cap10不变，剩余9.10902552元。历史unknown2保持、新unknown0、未freeze，本地控制calls0/count0/revision0。QA未直接读取ledger。

| Case | 真实回复质量 | 最终显示与依据 |
|---|---|---|
| C01 初始观察 | 事实失败；有用的单步方向、自然表达且未泄题 | 原文说“当前能直接看的只有实验记录”，实际7个可见物件；模型只收到1个focus，误把子集当完整场景。错误进入显示。 |
| C02 连问 | 事实失败、承接与引导不足 | 确实收到实际C01历史，但重复“唯一可直接观察的对象”并延续同一错误；没有合理解释为何优先记录。错误进入显示。 |
| C03 时间局部关系 | 通过 | 正确解释末两位与分钟的关系，引用clock+record，未报完整编号，不代操作。自然回应了当前问题。 |
| C04 柜码接受未开门 | 引用失败、交付失败 | 原正文正确解释CODE_ACCEPTED仍需拉柜门，但捏造不存在的r1_cabinet_clue。guard正确停止、count不增；玩家只看到通用失败，不能算质量成功。 |
| C05 线路局部 | 引用依据失败；正文方向正确 | 对相邻端口互惠朝向的说明正确且不泄线路数组；却引用r2_maintenance_clue，它只讲USER/PASS格式，不能支持线路几何。错误引用进入显示。 |
| C06 已登录未读 | 引用依据失败；正文方向正确 | UNLOCKED后读取记录的建议正确、简短且不要求重解密码；同样误引仅讲登录格式的maintenance，状态事实应来自公开装置而非该线索。 |
| C07 终检局部转录 | 通过 | 解释源符号→位置→设备的逐层映射，只示范第3位思路，3个引用相关，未列完整设备序列。 |
| L01 整组核对控制 | 本地边界通过，不计模型质量 | 0call、不计数/不改revision，拒绝判断整组答案。 |

六轴逐例记录见 `qa/first-batch-quality.json`：相关性、事实支撑、引导、不泄题、自然非模板、连问承接。7条原始回复均已读，6条模型文案显示、1条被挡；本批2例（C03/C07）满足全部适用质量项，5例有上述事实/引用/交付问题。不把技术status成功或guard拦截计为质量通过。未发现这7例报出完整解法或未发现故事内容。

窄修方向有必要：补全仅id/name的当前可见目录，明确focus细节是子集，禁止据此断言“唯一”；公开状态、操作和线路几何答复使用refs[]，仅实际支撑关系推理的线索允许引用。allowed_clue_refs不能只是原known_evidence IDs换名，否则C05/C06仍可误引。未知refs继续拒绝，不降低guard。最多一条新C08可兼测柜状态与场景范围，但只能作为该修正场景的样本，不能称C01/C02/C05/C06全部重测通过；旧7次结果/source保持历史。

## 窄修离线验证

Main固定候选 d4bf7c1c95f866118bed12b675b449d0fa53954dce0fbb8777992dee9884c2e5。QA实际运行 `C:\Users\liyh\.conda\envs\1\python.exe -B -X utf8 tests/ai-companion-real/run_regression.py evidence/integration/ai-companion-real/candidate-fixed.json`，首次14methods/8.687秒 exit0，failures/errors均0。原companion8、新目录/引用策略/Runtime+Store2、旧preset2/legacy2；243source前后、73旧test及首批旧artifact保持。证据qa/20261018T111053477549Z-fixed-regression/。不运行build/UI、不读canonical预算、无付费。

新增断言证明完整catalog对应当前publicobjects、C04/C05/C06状态/几何使用空refs、C03/C07正常关系保留支持refs、伪造柜clue继续拒绝；无关但已知的clock引用也被Runtime及Store拒绝。C08唯一新例的静态hash/AST/载荷核对exit0：CODE_ACCEPTED、catalog6、allowedrefs[]、reserve上界0.061096元≤0.20，首7+1总最多8。该GO不是实际模型质量结论，真实结果另审阅；详情qa/fixed-offline-and-target-preflight.json。

以下保留执行前协议；本批真实调用与旧unknown未重发。QA付费请求0、额外provider评委0，无真人试玩声称。

## 原审查协议

用户本轮已授权付费试玩；本轮最多1.50元、最多8次真实dispatch，原10元cap不增加。执行前Main报告剩余9.12574152元、历史unknown2，已由本批摘要算术和记录核对。

建议6至8个合法游戏状态case：初始观察、同状态连问、已知钟面21:17的局部关系、玻片/再次观察可选、R2线路局部端口、电脑已登录未读记录、R3终检局部转录关系；另完整答案判对错作为本地0call对照。先保存实际context preview并检查只含问题、授权历史、当前公开状态/已发现线索；新官方模型别名须先由Main验证并窄修允许，再执行真实call。

每条独立评价：回应当前问题、事实有依据、帮助玩家想出一个小步骤、不泄完整答案或未知事实、自然且没有照抄/仅改写模板、连问承接前轮（非连问记N/A）。用通过/不足/失败并给一句具体依据，不以相同空泛方向、反复拒绝或套模板视为质量合格；不调用额外provider当评委，不宣称真人试玩。

分别记录原始provider输出、最终显示输出及stop reason。模型已回答但guard挡住，说明边界生效，也计入真实可用性问题；不得只展示成功样本。首次结果失败不自动重试/改问题重打，不为凑满数量增加调用。新增unknown、allowlist/budget freeze或泄题立即停止，历史unknown2不重发；若因此完成不足6例，按真实数量交付。

Main结果至少应提供：冻结source与artifact哈希、逐case公开before state/context/question/expected focus、原始与最终reply路径、request/turn/call关联、实际dispatch数、usage/charged/reserved成本、预算before/after和unknown变化、停止原因。本地完整猜测控制必须calls0、count/revision不变且不进入成功对话。预算结论来自实际ledger摘要，不能把上界当实付。

新review_result.py仅用stdlib读取已脱敏结果，核对文件hash、次数/费用边界、来源路径和本地对照；语义质量另逐条阅读。最终结果只适用于这批真实问题与状态，不认证所有自然语言安全、未来模型版本或真人体验时间。本轮不重跑旧suite、构建、手机矩阵，不提交产品修改。

静态preflight结论：GO，非质量接受。最终runner SHA9385dd8e220dffb8e3587640c8caaca932f06b1969c68e55798534efbfd1d143、preview SHA2b122b8a596582823001894e0e1f09ebb81e21fba863ad9bf29111eb7f2e0592均匹配，AST检查exit0。7真实+1本地载荷阶段与已知refs正确；初始最坏reserve合计0.34096元，执行前仍逐call重算。先前并发编辑导致的hash不同及原始回复停止检查的变体缺口均已收敛，详见qa/preflight-review.json。QA没有执行runner、付费或读取ledger。
