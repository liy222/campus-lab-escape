# 交付索引

项目仍处于开发阶段，尚非最终交付。产品冻结基线为 `7821af4efe0613c20a80ea164c1dab1c0f288bab`；T22 实验工程提交为 `d20a1f17e121dcd672e4af1196699618fa5ba818`。产品基线身份信息见 `evidence/integration/baseline_v1-manifest.json`。

## 源码与入口

- `backend/app/` 和 `frontend/`：本机游戏服务及三房间网页界面；`scripts/` 提供开发与本地检查工具。
- `experiments/`：冻结样本、预试和正式计划、模拟执行与受限真实调用入口。命令为 `python -m experiments.runner check|plan|pilot|mock|run|summarize|reconcile`。真实模式须有针对当前 phase 和输入的有效 Main 有限 gate。
- `evaluation/`：只读登记证据的预检、确定性评价和校准。命令为 `python -m evaluation.cli precheck|evaluate|calibrate`；付费模式须经可信配置中的有限 gate。入口与模式说明见 `evaluation/README.md`。
- `docs/SPEC.md`、`docs/level_design.md`、`contracts/`：产品和机器可读契约；`docs/execution-plan.md` 是接受的范围说明，不是执行证明。

## 独立检查与证据

- T21 产品身份与修正事实见 `evidence/index-M0.json`、`evidence/integration/baseline_v1-manifest.json` 和 `review/findings/T21-identity-review-20261002.md`。
- T22 实验工程独立 QA 为 764 项通过、进程 exit 0，83 条源记录一致：`evidence/qa/T22-experiments-20261002T164754631028Z/{result,process-result}.json`。T22-EXP-001 已关闭：`review/findings/T22-acceptance-20261003.md`。
- T26 评价器工程独立 QA 为 193 项通过、进程 exit 0，34 条源记录一致；T26-EVAL-001 和 T26-EVAL-002 均关闭：`evidence/qa/T26-evaluation-20261002T165331450690Z/{result,process-result}.json`、`review/findings/T26-acceptance-20261003.md`。该 QA 没有运行目标 backend、读取凭据或原预算账本，也没有网络/付费调用。
- 交付索引本次核对记录在 `evidence/delivery/T26-index-20261005/`。

## 尚未完成

T23 旧 pilot 因 quota 未运行，旧 gate 已过期；不能把它作为新的真实调用授权。原预算账本仍记录 6 条历史调用。真实 E1 对比实验、评价器付费校准、CH01 对抗复测及最终交付仍未完成，须由 Main 后续建立适用的有限授权。真实模型效果、费用和自然模型抗注入表现不由工程 QA 推断。

真人试玩、玩家接受或拒绝 AI 建议的实际记录及人类签署尚未提供，不作完成声明。课程确认无需处理。没有公开部署。
