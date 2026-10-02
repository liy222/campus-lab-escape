# 交付索引

项目仍在正式开发，不是最终交付。此页按六类材料指向当前事实；完整范围以实际证据为准。产品冻结基线为 `7821af4efe0613c20a80ea164c1dab1c0f288bab`，T21 元数据修正已同步至 `9702fe39432aa78fc7286f796aa11c616355ec84`。T21 独立校正结论见 `review/findings/T21-identity-review-20261002.md`；产品 baseline v1 manifest 和 60 个源码身份未因元数据校正而改写。

## 源码

- `backend/app/`：游戏规则、API、SQLite 存储和 AI Provider。
- `frontend/`：三房间浏览器界面；`scripts/` 提供本机开发、确定性检查、依赖锁定与受限数据重置入口。
- `experiments/`：E1 冻结样本、A/B 输入构造、预试/正式计划、受限真实调用门和逐行汇总。入口：`python -m experiments.runner check|plan|pilot`，另有 `mock`、`run`、`summarize`、`reconcile` 子命令。真实模式需 Main 为该 phase 提供一次性有限授权。
- `evaluation/`：只读登记证据的预检、确定性评价、判读与校准入口：`python -m evaluation.cli precheck|evaluate|calibrate`。评价器仍是 Owner 候选；T26-EVAL-002 待修复和独立复测。
- 所有付费路径共用原账本和预算。不得以 mock/fake 或 Owner 检查描述真实模型效果。

## 契约

- `docs/SPEC.md`、`docs/level_design.md`、`contracts/`：产品、关卡和机器可读接口契约。
- `docs/execution-plan.md`：接受的项目范围与课程材料要求；计划文本不代表执行证据。
- `evaluation/trusted/`：冻结的评价器契约、输入 pin 和可信 gate 配置。当前 `paid-gates.json` 没有付费批准。

## 检查

- M0 基线及 M1/M2/M3 的阶段性结果保存在 `evidence/` 与 `review/findings/`；各报告注明其实际候选版本、范围和限制。
- T21 元数据校正独立复核：`evidence/qa/T21-identity-correction-review-20261002.json`，结论见 `review/findings/T21-identity-review-20261002.md`。
- T22 实验工程独立复跑：`evidence/qa/T22-experiments-20261002T164754631028Z/result.json` 与 `process-result.json`；764 项通过、进程 exit 0、83 条源记录运行前后相同。它覆盖工程门、输入与合成传输，不表示任何真实实验结果。
- T26 评价器独立复核：`review/findings/T26-EVAL-002-unvalidated-audit-suggestion.md`。179 项中一项失败，发现非法模型建议字段可能进入审计对象；Owner 修复及独立复测待完成，不能称评价器 QA 全通过。
- 此索引没有把旧阶段的通过结果扩展到后续功能；正式 QA 只在各候选稳定后报告。

## 证据

- `evidence/index-M0.json` 与 `evidence/integration/baseline_v1-manifest.json`：接受的产品基线及其身份绑定。
- `evidence/delivery/T22-index-20261003/`：本次索引更新的文件 SHA-256 与核对命令记录。
- `evidence/qa/`、`evidence/provider/`、`evidence/backend/`、`evidence/frontend/`：阶段性 QA、Provider 和 Owner 证据。文件存在本身不扩大报告中的验收范围。
- `experiments/runs/` 中的已有计划、mock 和合成故障记录只作本地工程材料；真实 pilot 与 formal 尚未执行。
- `evaluation/runs/` 中的 Owner 结果不是独立验收、真实校准或正式 E1 判读。

## 变更

- T21 修正只更新派生验收事实和附录，保留原始 manifest 与源证据；产品提交和标签仍为 `7821af4`。
- T22 实验范围独立 QA 已通过；预试与正式调用仍需之后的有限授权。
- T26-EVAL-002 保持开放，由 Evaluator Owner 修复；完成后须由独立 QA 复测。
- CH01 有限变更、对抗复测和干净目录交接尚未完成。Git 与项目状态文件由 Main 维护。

## 报告与剩余工作

- `STATUS.md`、`PLAN.md`、`DECISIONS.md`：项目当前状态、计划和 Main 决策。
- 仍待完成：评价器修复及独立复测；受控真实 pilot 和 72 行正式 E1 实验；真实 paid 校准/正式评价（须另获 Main 有限 GO）；CH01 与对抗复测；干净目录安装和恢复交接。
- 真人试玩、玩家接受/拒绝 AI 建议的实际决策记录、人类签署和教师批准未提供，不由软件或 Agent 推断。课程确认已按用户指示从阻塞项中移除。
- 没有公开部署。上述未决事项完成前，不声明整体交付或项目完成。
