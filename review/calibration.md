## 2026-10-06 新提示版本补充（不覆盖旧报告）

提示版本 `2e9778f186c8191a475db9fa359a06dea8725cd4733872c450bf261d0cbfb74c` 的有限结果：校准报告 `evaluation/runs/20261006T043749352975Z/report.json` 实际3次付费调用；11个校准检查为3条真实模型结果加8项确定性对照，11/11匹配，不是11次付费校准。E1 `evaluation/runs/20261006T043806611760Z/report.json` 实际2条PASS，绑定原冻结计划状态行：22 completed、1 timeout、49 not_called，不代表72次均完成或对merged69新run重新判读。CH01 `evaluation/runs/20261006T043822902164Z/report.json` 实际3条PASS，仅为登记工程Claim判读。三份结果经 `review/findings/T27-revised-real-result-20261006.md` / `evidence/qa/T27-revised-real-result-20261006T045000Z/result.json` 独立 QA 75/75、exit 0、SOURCE STOP；原始旧6次判读及旧校准10/11报告保持原样，不重发。人工签署与教师批准仍为null。

# T27 校准审查草案

## 2026-10-06 当前有限真实记录与提示修正

Main 明确批准后的旧源真实校准报告 `evaluation/runs/20261005T120430742113Z/report.json` 保留11案例/10匹配、实际程序 exit1，实际仅2次付费。K1 引用未通过严格复核而证据不足；K2 模型不可用、usage未知，由确定性失败判 FAIL；K4 当时因 prior unknown 门停止且未调用。之后单独批准的剩余 K4 在 `evidence/integration/remaining-k4-20261005.json` 实际1次付费，合法模型 FAIL 引用 `calibration_v1:F004/summary`，usage已知。校准历史累计3次付费是原2次加后来的1次，不重写原10/11报告，不称完整校准通过或评分。

同一旧源后续 E1 `evaluation/runs/20261005T155830386817Z/report.json` 两次、CH01 `evaluation/runs/20261005T155947272680Z/report.json` 三次实际判读均为 INSUFFICIENT_EVIDENCE，共5条事件语义弃权；错误包括未读取/假引用、schema/provider错误、1000输出token的 MODEL_INVALID_OUTPUT。原始失败、有限批准记录、实际usage/null和独立QA首轮错误均保留。既有未知调用的保守会计关闭不提供供应商账单、不恢复未知usage，也不改变判读历史。独立只读审查见 `review/findings/T27-real-calibration-20261005.md`、`review/findings/T27-remaining-evaluation-20261006.md`。

本次 Main 临时单文件 handoff 后的 Evaluator Owner 修正只明确 `snippet` 是注册窗口 ID，要求引用来自 Tools 已实际核验的 pair，并提供原冻结 suggestion Schema 与简短紧凑输出提示。`TRUSTED_OUTPUT_CONTRACT` 位于 TARGET_DATA 外，rubric/target数据原内容保留。没有改 Schema、契约、fixtures、expected、reader、provider、事件冻结、paid gates 或严格校验/失败优先规则；没有新增付费调用。当时这段文字描述的是离线修正刚完成时的历史状态；后续有限真实判读和独立QA另见本文开头补充，不能把离线QA本身当作真实模型验证。

以下为先前草案的历史状态文字，保留其当时范围；不作为当前空gate或未发生付费的声明。

此文件由 Main 明确 handoff 给 Evaluator 起草。旧 T26 候选已有独立 QA 接受（193 项、34 源，实际 exit 0，`review/findings/T26-acceptance-20261003.md`）。校准仍是显式 mock/fake Transport；新增事件层尚待独立 QA，尚无真实付费 LLM 校准或真人签署。

输入冻结在 `evaluation/trusted/freeze.json`；11 个 K1–K6 子案例及预期先于判读调用保存，集合 SHA-256 为 `58423418e0f336899fbeffc1439f007f73bd4206d54f09e10121235dc56fabe1`。expected 不送模型。K1引用实际项目 build/check 证据，K2/K4等合成材料明确标注，不是项目执行事实。

K4要求保存模型原始结构建议与最终判定，并证明已进入判读路径；明确失败不能被“判 PASS”注入覆盖。K5拒绝错 ID/版本/hash；K6批准只针对合成校准可选项，不能豁免真实项目 MUST 或人类签署。

后续：Main 冻结稳定实现并交独立 QA 检查边界及预算协议；之后 Main 另给有限真实付费校准门，记录 K1–K6 的逐项实际结果、误放行、错误失败、不必要弃权和引用。E1证据另行冻结登记后才能正式审查。当前四状态报告仅为工程审查，不是课程总分。

2026-10-05 的事件扩展保持旧冻结输入与预期原字节，新增默认空、仅 Main exact pin 可登记的 `events-registry-v1`、每事件完整 freeze 和 Main 固定 runtime 身份映射。可选 archive 映射保留真实原路径 before/after 与精确 raw/Git 身份；归档本身不证明执行。2–3 条事件 Claim 保留可信 MUST，部分范围返回不足。事件 paid gate 绑定整个 freeze raw hash，旧校准 gate 语义不变。

Main 已告知正式 E1 因不确定调用停止，实际调用、完成、超时和未调用行须原样保留；该段登记与停止状态描述的是当时阶段；后续E1两条有限判读见本文2026-10-06补充。原计划仍为22 completed、1 timeout、49 not_called，不能称为72次成功。Main 已告知原不确定调用完成手工保守关闭；此处未读取原账本，未来任何 paid 仍须独立有限 gate，此次不授予paid。本次只执行 offline Owner 检查，synthetic fixture 与其 Main 字段明确为隔离合成材料，真实v2登记仅来自Main固定路径/rawSHA，不写假生产批准。准确登记字段与模板在 `evaluation/runs/20261005-event-main-handoff-v2/`。

`human_signoff: null`；`teacher_approval: null`。本草案无真实模型校准结论或替人签署。

Main批准最小legacy归档桥接后，旧114项Owner检查与11案例mock恢复；源码核验明确读取固定60条v1 archive，不认证当前CH01源码，也不声称archive执行。原current漂移拒绝与v2公开.gitignore首次拒绝证据保留。新事件archive actualraw严格校验不采用CRLF canonical fallback；102source/6execution与historical identity provenance完整保留。独立QA尚待审查新增稳定候选。
