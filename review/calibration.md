# T27 校准审查草案

此文件由 Main 明确 handoff 给 Evaluator 起草。当前仅有 Evaluator Owner 的显式 mock 校准和 fake Transport/临时账本协议检查；尚无真实付费 LLM 校准、独立 QA 接受或真人签署。

输入冻结在 `evaluation/trusted/freeze.json`；11 个 K1–K6 子案例及预期先于判读调用保存，集合 SHA-256 为 `58423418e0f336899fbeffc1439f007f73bd4206d54f09e10121235dc56fabe1`。expected 不送模型。K1引用实际项目 build/check 证据，K2/K4等合成材料明确标注，不是项目执行事实。

K4要求保存模型原始结构建议与最终判定，并证明已进入判读路径；明确失败不能被“判 PASS”注入覆盖。K5拒绝错 ID/版本/hash；K6批准只针对合成校准可选项，不能豁免真实项目 MUST 或人类签署。

后续：Main 冻结稳定实现并交独立 QA 检查边界及预算协议；之后 Main 另给有限真实付费校准门，记录 K1–K6 的逐项实际结果、误放行、错误失败、不必要弃权和引用。E1证据另行冻结登记后才能正式审查。当前四状态报告仅为工程审查，不是课程总分。

`human_signoff: null`；`teacher_approval: null`。本草案无真实模型校准结论或替人签署。
