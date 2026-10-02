# 逃离校园实验室

三房间网页解谜游戏具备手动通关、保存恢复、AI提案确认和受限模型接入。产品基线是 `7821af4efe0613c20a80ea164c1dab1c0f288bab`；当前已同步的 T21 元数据修正提交为 `9702fe39432aa78fc7286f796aa11c616355ec84`。基线身份与校正证据见 [`evidence/index-M0.json`](evidence/index-M0.json)、[`evidence/integration/baseline_v1-manifest.json`](evidence/integration/baseline_v1-manifest.json) 和 [`review/findings/T21-identity-review-20261002.md`](review/findings/T21-identity-review-20261002.md)。

## 本地运行

在 PowerShell 中使用已配置的 Python 和 Node 环境：

```powershell
Set-Location -LiteralPath 'D:\深度能力'
$ProjectPython = 'C:\Users\liyh\.conda\envs\1\python.exe'
& $ProjectPython -m pip install -r backend/requirements.lock.txt
npm.cmd --prefix frontend ci
& $ProjectPython -m scripts.dev --provider mock
```

打开 <http://127.0.0.1:5173/>。服务只监听本机。按 Ctrl+C 停止。完整安装、保存恢复和安全说明见 [`release/README.md`](release/README.md)。数据重置会删除游戏数据，只在理解其影响后按 release 文档指定的命令操作。

## 已验证与进行中

- T21 身份元数据修正已独立复核通过；产品基线仍为 `7821af4`，修正后的已同步提交为 `9702fe3`。
- T22 实验工程独立检查现有记录为 764 项通过、exit 0，证据在 [`evidence/qa/T22-experiments-20261002T164754631028Z/`](evidence/qa/T22-experiments-20261002T164754631028Z/)；这验证工程逻辑与模拟传输，不代表真实模型预试或正式实验已执行。
- 评价器仍是 Owner 本地候选。独立 179 项检查发现 T26-EVAL-002：非法建议中未经校验的字段会反映进审计对象；当前由 Owner 修复，尚未独立全通过。修复前不运行付费校准。
- 实验真实预试和 72 行正式实验未执行。实验实现入口为 `python -m experiments.runner check|plan|pilot`；任何 `--mode real` 运行需要 Main 的有限授权门。
- 评价器入口为 `python -m evaluation.cli precheck|evaluate|calibrate`；当前可信付费 gate 为空，尚无真实校准或正式判读。
- 真人试玩、AI 建议接受或拒绝记录、人类签署和教师批准尚未提供。课程确认已从当前阻塞项中移除。项目仍在开发，尚非最终交付；没有公开部署。

版本、六类材料和当前验收界限见 [`release/README.md`](release/README.md)。每份证据只支持其中明确标注的范围；Owner 检查不等于独立 QA，模拟结果不等于真实调用。
