# SP-01 纹理动态补载：主题分支探索记录

范围澄清：本文记录较早的theme pack探索，不能代替原始generic缺陷复验；最终闭环见[generic窄补](qa-generic-texture-fix.md)。下文保留当时执行与判断，原始result/PNG未改。

当时状态：Main发现的加载问题已由Frontend修复，并通过主题分支浏览器复核。旧SP-01的49项/20项/11项和原截图均未重跑或覆盖。真实用户验收仍待本人。

## 执行

- Frontend于GeneratedScene.tsx SOURCE STOP后，按Main GO执行唯一一次`frontend` V5构建：`npm run build`，`VITE_GAMEPLAY_VERSION=v5`、`CAMPUS_BACKEND_URL=http://127.0.0.1:8001`，exit0；仍有Phaser大chunk提示。结果见`automated/qa-texture-fix-v5-build-result.json`及对应log。
- 新runner只增加`--reveal-only`分支：使用雨夜天文社Synthetic R3缓存，沿已验证witness完成取钥匙、查看新显现观察资料、完成G1门禁，在首个move前和跨入G2后检查当前纹理状态；未改产品代码、未重跑普通11项。
- 最终浏览器命令：`node tests/v5/run_passage_semantics_browser.mjs --reveal-only`，exit0，13/13检查通过。所有阶段等待`data-loading-textures=false`，均观察`data-missing-textures=0`；G1每次状态变化后当前主题variant aliases均存在（首次4/4，后续6/6），G2切换后当前aliases 3/3。门禁真实UI动作后仅发送一次move到G2。背景URL由`neutral_lab.png`切至素材清单的`neutral_archive.png`。外部请求0，0付费/真实模型调用，玩家库访问0，自有8002服务已停止。
- 唯一结果目录`automated/qa-browser-2026-10-29T15-50-50-233Z-7a3234d7/`保存13条安全记录、6张截图与结果JSON。重点截图：`qa-browser-R3-reveal-take-shared_key.png`、`qa-browser-R3-reveal-inspect-obj_relation.png`、`qa-browser-R3-reveal-submit_sequence-puzzle_5.png`、`qa-browser-R3-G2-background-textures.png`。

## 保留的QA尝试与范围说明

首个reveal-only尝试使用`SP synthetic passage 3`，未匹配天文社主题包；此时model为generic，因而theme variant计数为0。missing=0，表示无实际缺图；QA的主题alias前置断言不适用于generic，运行exit1。这个结果原目录保留。随后换成项目已有、被认可的雨夜天文社主题，在新的TEMP副本缓存上重跑并通过。未将首次失败伪装成通过或删除。

本补丁只证明指定Synthetic witness和两个房间间的纹理加载/背景变化，不代表任意AI输出或真人试玩接受；画风认可不等于本阶段真人验收。

请本人试玩时重点观察拿到钥匙、出现新资料与门禁完成后的场景，以及进入资料室后背景是否切换正常。
