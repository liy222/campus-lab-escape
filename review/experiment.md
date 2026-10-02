# E1 实验复核草案 — 未执行

此文件由 Main 明确 handoff 给 Experiments，仅为 T25 复核框架。T22 正在完成本地候选；T23/T24 真实模型实验尚未执行，以下不是结果、通过声明或预算批准。

待独立 QA 核对公开输入与离线资料隔离、12点来源与版本、可逆历史事实相等、六工具 schema、72行完整性、配对顺序及6行独立pilot、错误/未知/未调用保留、分母、共享原账本、有限GO、崩溃对账无重打。Owner check 与注入 mock 不能替代独立 QA 或模型观察。

T25真实结果到达后，逐条引用不可覆盖的 plan/run/input/raw/journal/summary 指纹；报告每方案 planned、付费尝试确证下界/未知、收到响应、completed、legal、correct、有效引用与用量覆盖，列举所有失败和 budget-stop。动作正确性与自由文本幻觉范围、费用上界与实际账单明确区分。不得预先填写摘要优势。

基线源码绑定依据 Main 的 `evidence/integration/baseline_v1-manifest.json`，raw SHA256 `9c36943cbb6e4fe08b6e176445ba91835fafa79a2077c2155bbf8d613f8b07c1`。其中6条旧 QA 源码记录未绑定原样保留，3个构建输出仅 runtime binding；本草案不消除这些局限。Main 最近修正的 metadata facts 不改变 baseline product，不把旧 paid scope 当实验事实。

决定留空，待 T24、QA 只读复核和 Main 确认。不证明统计普遍性、总体智能、自主通关、真人签署或课程批准。

2026-10-02独立Finding T22-EXP-001真实复现HTTP响应记录缺陷：Owner已按授权修复实验层，增加安全transport receipt观察和响应/投递三态汇总。本条不是独立复测通过声明；旧149项Owner证据及QA首轮12失败证据保留。新增Owner注入HTTP错误、坏JSON、连接错误/超时/未调用的检查仍是本地模拟，付费调用0。等待QA独立稳定复测。
