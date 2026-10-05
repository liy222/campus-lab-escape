# 逃离校园实验室

三房间网页解谜游戏支持手动通关、保存恢复、AI 提案确认和受限模型接入。接受的产品 v1 基线仍为 `7821af4efe0613c20a80ea164c1dab1c0f288bab`；T22 工程提交为 `d20a1f17e121dcd672e4af1196699618fa5ba818`。T21 身份及元数据核对见 `evidence/index-M0.json`、`evidence/integration/baseline_v1-manifest.json` 和 `review/findings/T21-identity-review-20261002.md`。

## 本地运行

在 PowerShell 中使用现有 Python 与 Node 环境：

```powershell
Set-Location -LiteralPath 'D:\深度能力'
$ProjectPython = 'C:\Users\liyh\.conda\envs\1\python.exe'
& $ProjectPython -m pip install -r backend/requirements.lock.txt
npm.cmd --prefix frontend ci
& $ProjectPython -m scripts.dev --provider mock
```

打开 <http://127.0.0.1:5173/>。安装、恢复和受限重置说明见 [`release/README.md`](release/README.md)。

## 当前证据与状态

- T22 实验工程独立 QA 通过：764 项、进程 exit 0，83 条源记录运行前后相同；证据位于 `evidence/qa/T22-experiments-20261002T164754631028Z/`，Finding 在 `review/findings/T22-acceptance-20261003.md` 关闭。这不代表真实实验已运行。
- T26 评价器工程独立 QA 通过：193 项、0 失败、进程 exit 0，34 条源记录一致；`T26-EVAL-001` 与 `T26-EVAL-002` 均关闭。证据为 `evidence/qa/T26-evaluation-20261002T165331450690Z/{result,process-result}.json`，验收说明见 `review/findings/T26-acceptance-20261003.md`。本次未作网络或付费调用。
- T23 旧 pilot 因 quota 未运行；旧有限 gate 已过期，不能授权新的真实运行。原预算账本仍记有 6 条历史调用。真实 E1 实验、评价器付费校准、CH01 对抗复测和最终交付尚未完成；这些都需要之后由 Main 决定的有限授权门。
- 真人试玩、玩家对 AI 建议的实际决定和人类签署未提供，本文不作此类完成声明。没有公开部署。

六类材料索引、入口和证据范围见 [`release/README.md`](release/README.md)；索引核对记录见 `evidence/delivery/T26-index-20261005/`。
