# T27 校准审查草案

此文件由 Main 明确 handoff 给 Evaluator 起草。旧 T26 候选已有独立 QA 接受（193 项、34 源，实际 exit 0，`review/findings/T26-acceptance-20261003.md`）。校准仍是显式 mock/fake Transport；新增事件层尚待独立 QA，尚无真实付费 LLM 校准或真人签署。

输入冻结在 `evaluation/trusted/freeze.json`；11 个 K1–K6 子案例及预期先于判读调用保存，集合 SHA-256 为 `58423418e0f336899fbeffc1439f007f73bd4206d54f09e10121235dc56fabe1`。expected 不送模型。K1引用实际项目 build/check 证据，K2/K4等合成材料明确标注，不是项目执行事实。

K4要求保存模型原始结构建议与最终判定，并证明已进入判读路径；明确失败不能被“判 PASS”注入覆盖。K5拒绝错 ID/版本/hash；K6批准只针对合成校准可选项，不能豁免真实项目 MUST 或人类签署。

后续：Main 冻结稳定实现并交独立 QA 检查边界及预算协议；之后 Main 另给有限真实付费校准门，记录 K1–K6 的逐项实际结果、误放行、错误失败、不必要弃权和引用。E1证据另行冻结登记后才能正式审查。当前四状态报告仅为工程审查，不是课程总分。

2026-10-05 的事件扩展保持旧冻结输入与预期原字节，新增默认空、仅 Main exact pin 可登记的 `events-registry-v1`、每事件完整 freeze 和 Main 固定 runtime 身份映射。可选 archive 映射保留真实原路径 before/after 与精确 raw/Git 身份；归档本身不证明执行。2–3 条事件 Claim 保留可信 MUST，部分范围返回不足。事件 paid gate 绑定整个 freeze raw hash，旧校准 gate 语义不变。

Main 已告知正式 E1 因不确定调用停止，实际调用、完成、超时和未调用行须原样保留；本评价器现仅登记 Main exact pin 的 E1-formal-review-v2，尚无真实付费语义判读，不能将停止数据称为 72 次成功。Main 已告知原不确定调用完成手工保守关闭；此处未读取原账本，未来任何 paid 仍须独立有限 gate，此次不授予paid。本次只执行 offline Owner 检查，synthetic fixture 与其 Main 字段明确为隔离合成材料，真实v2登记仅来自Main固定路径/rawSHA，不写假生产批准。准确登记字段与模板在 `evaluation/runs/20261005-event-main-handoff-v2/`。

`human_signoff: null`；`teacher_approval: null`。本草案无真实模型校准结论或替人签署。

Main批准最小legacy归档桥接后，旧114项Owner检查与11案例mock恢复；源码核验明确读取固定60条v1 archive，不认证当前CH01源码，也不声称archive执行。原current漂移拒绝与v2公开.gitignore首次拒绝证据保留。新事件archive actualraw严格校验不采用CRLF canonical fallback；102source/6execution与historical identity provenance完整保留。独立QA尚待审查新增稳定候选。
