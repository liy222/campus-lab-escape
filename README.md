# 逃离校园实验室

校园主题密室逃脱桌面网页项目，使用 React / TypeScript / Phaser、FastAPI 与 SQLite。复用规则后端、账号、AI伙伴和存档体系，通过程序约束合法关卡结构，由AI生成故事、名称与谜面参数。

**老师评阅：[课程材料与证据索引](docs/TEACHER-REVIEW.md)**。需求、规格、ADR、Harness、任务、代码、实验、评价和真人截图均在仓库中，历史失败及修复记录保留原范围。

## 当前功能与状态

- 经典三房间；生成关卡支持五类校园主题、1–3房间及难度选择。程序负责合法骨架、答案、证明/回放和操作说明，AI负责有限结构内的内容变化。
- 五主题手绘场景与物件共74张独立原图，背景及外观有有限候选，按关卡稳定选择；刷新和读档保持一致，素材允许重复。
- 本机账号注册/登录、私人进度、多时刻存档/读取/删除、免费三级提示与可选真实AI伙伴。
- 作者主动发布到共享大厅，其他本机账号独立挑战；每关卡记录每账号最快连续用时，标注作者及辅助使用。同轮读档继续计时，跨轮读档转练习；取消共享后已有参与者仍可继续。

最新功能提交为 `cd0c238`，11月5日本人反馈于 `eea8e97` 归档。本人已确认共享、连续计时、排行榜、跨轮练习和取消共享后的入口规则；[原话及时间顺序原图](evidence/project/human-reviews/v5-sharing-leaderboard/round-01/review.md)。本次将开发分支的81个提交快进合并至 `main`，完整保留提交历史。

仅支持桌面鼠标/键盘，目标尺寸1280×720、1920×1080。当前是本机开发版本，无发布tag、公网部署或Actions；技术结果和局部本人反馈不等于整版发布验收。[当前状态](STATUS.md) · [计划与剩余边界](PLAN.md) · [功能/26项要求证据](docs/V5-DELIVERY.md)。

## 本地运行

在现有项目环境中双击 [启动新版.cmd](启动新版.cmd)，健康检查通过后打开 [游戏入口](http://127.0.0.1:8001/)。网页需服务运行，不能双击游戏HTML替代后端。启动器复用依赖和 `frontend/dist-v5/`，不自动安装或构建。

首次克隆若尚无依赖及构建，在仓库根目录执行以下准备；已有环境无需重复：

```powershell
& 'C:\Users\liyh\.conda\envs\1\python.exe' -m pip install -r backend/requirements.lock.txt
npm.cmd --prefix frontend ci
$env:VITE_GAMEPLAY_VERSION = 'v5'
$env:CAMPUS_BACKEND_URL = 'http://127.0.0.1:8001'
npm.cmd --prefix frontend run build
& 'C:\Users\liyh\.conda\envs\1\python.exe' -B -X utf8 -m scripts.run_v5 --open-browser
```

其他电脑将Python路径换为自己的环境。开发模式使用 `-m scripts.run_v5 --dev --open-browser`，前端地址为 `http://127.0.0.1:5174/`。经典版使用 [启动游戏.cmd](启动游戏.cmd)；更多运行与数据政策见 [V5说明](release/V5.md)。无需服务的素材预览可双击 [美术图集.html](美术图集.html)。

账号、关卡和存档在本机服务保存。V5为 `data/game-v5.sqlite`，经典库独立保留；共享升级前保存一致性备份，不将数据库提交Git。经典玩法、已生成关卡、免费提示无需Key；新生成与真实伙伴需玩家临时输入Key并使用自己的额度，不自动付费重试。不要将服务直接暴露到公网。

## 文档与材料

| 入口 | 用途 |
|---|---|
| [老师评阅索引](docs/TEACHER-REVIEW.md) | 按课程要求阅读设计、实现及实际证据 |
| [正式构建计划](docs/v5-build-plan.md) / [共享扩展规格](docs/v5-sharing-leaderboard-plan.md) | 范围、规则、任务依赖、验收与边界 |
| [PLAN](PLAN.md) / [STATUS](STATUS.md) / [DECISIONS](DECISIONS.md) / [AGENTS](AGENTS.md) | 当前进度、历史决策与开发约定 |
| [固定证据入口](evidence/project/README.md) / [阶段索引](evidence/project/index.json) | 自动结果、日志、实验、评价及真人核验 |
| [接口合同](contracts/v2/README.md) / [观测与评价标准](docs/v5-evaluation.md) | 类型/路由和生成阶段观测方式 |
| [实验](experiments/v5/README.md) / [评价器](evaluation/v5/README.md) | 有限工程实验和来源固定的C1–C3评价 |
| [原始根文档归档](docs/history/repository-notes-20261111/README.md) | 精简前的完整正文、来源及原字节 |

旧测试与付费评价仅说明对应源码及样本。11月2日C1–C3真实评价3/3 PASS不覆盖后加的共享代码；六次生成样本全部通过也不是普遍成功率统计。五主题整体体验、普遍AI质量及真人时长/难度仍有未确认范围。后续按实际改动做必要定向验证，不因文档整理重复全套测试或付费调用。
