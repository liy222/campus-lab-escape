# SP-01 generic 场景纹理缺陷窄补 QA

状态：针对Main复核发现的generic场景动态纹理缺陷，Frontend SOURCE STOP修复后已按GO通过定向复核。此前49/20/11项均未重跑；旧result和原截图未覆盖。真人核验未发生。

## 范围与实际结果

- 本次仅在[run_passage_semantics_browser.mjs](../../../../../tests/v5/run_passage_semantics_browser.mjs)添加`--reveal-only`检查，按实际R3公开state顺序和art_id计算`legacy:<neutral asset id>:<index>`预期别名。测试对象为generic分支；不借雨夜主题包替代原问题。
- 按GO执行一次V5 `npm run build`，`VITE_GAMEPLAY_VERSION=v5`、`CAMPUS_BACKEND_URL=http://127.0.0.1:8001`，exit0。仍有Phaser chunk>500k提示。日志与摘要在`automated/qa-texture-fix-v5-build.log`、`automated/qa-texture-fix-v5-build-result.json`。
- `node tests/v5/run_passage_semantics_browser.mjs --reveal-only`最终exit0、13/13检查通过。沿用专用TEMP中的R3 synthetic draft/witness：take钥匙后4/4当前legacy aliases存在；使用钥匙、查看obj_relation、提交门禁顺序后各检查missing=0、loading=false及当前对象别名6/6；门禁已开启；真实UI点击只发送一次move到G2；G2加载当前3/3 aliases，missing=0、loading=false，背景src从`/art-handpainted/backgrounds/r1-room-shell.png`切为目录里`neutral_archive`对应的`/art-handpainted/backgrounds/r2-room-shell-off.png`。外部请求0；自有8002服务已停止；真实调用/付费0、玩家库访问0。
- 全部执行记录、问题和截图在唯一目录`automated/qa-browser-2026-10-29T15-53-44-556Z-461a8bc6/`。截图包括拿钥匙、打开新显现资料、完成前厅6门禁终端和进入G2后的场景。

## 失败记录和限制

一次早期generic尝试只检查了`theme:<variant>`，在generic场景没有主题variant时因此exit1；该断言方向不适用于generic。没有产品缺图数据（当时missing=0）。随后根据实际scene模型的legacy别名合同修正QA helper，使用新TEMP重跑同一R3受影响范围并通过。该失败目录保留，未覆盖。

验证覆盖指定Synthetic R3 witness及G1→G2，不代表其他输出或真人试玩接受。请本人核验拿到钥匙、新资料出现、门禁打开及进入资料室后的画面。本轮技术通过不等于真人接受。
## 分支参数映射

因本次result JSON已按唯一run目录封存，未改写原结果。各次实际的主题输入、scope、命令、TEMP缓存与结果路径以`automated/qa-texture-branch-index.json`为索引：

- 主题探索分支：`scene_theme=雨夜里的天文社旧活动室，寻找封存的观测记录`，exit0。它证明theme pack分支自身纹理加载，但不覆盖generic问题。
- generic最初断言尝试：`scene_theme=SP synthetic passage 3`，exit1。失败原因为QA期望错误使用`theme:<variant>`而非generic的legacy aliases；实际missing为0。原目录保留。
- generic问题闭合运行：`scene_theme=SP synthetic passage 3`，exit0、13/13。用当前公开对象按真实scene顺序及art_id派生legacy aliases，检测门禁解锁和跨房背景src。运行器内部fixture环境继续设置`SP_BROWSER_FIXTURE=1`、`GAMEPLAY_VERSION=v5`、`AI_PROVIDER=mock`、隔离SQLite路径；TEMP缓存使用合成JSON与自有临时fixture数据，本次只回放R3。

Main整理说明：分支索引中最初失败目录的时间部分已按实际文件更正为15-50-18-256Z；原始result/PNG未修改。早期主题分支与当前generic helper属于不同检查器源码时点，当前命令复现generic范围。
