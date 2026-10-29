# SP-01 独立QA报告

状态：限定范围自动验证完成，候选待Main复核；真人体验仍待本人检查。

## 实际执行与结果

- 新语义模块：`C:\Users\liyh\.conda\envs\1\python.exe -B -X utf8 -m pytest -q tests/v5/test_passage_semantics.py`。首轮exit1（47 passed/2 failed）：两个新见证用例漏传GeneratedRules.visible_state的合成会话ID；只修测试调用后按要求重跑，exit0，49 passed、1条Starlette/httpx弃用warning。首轮失败及最终结果分别见`automated/qa-pytest-first-attempt.json`、`automated/qa-pytest.log`和`automated/qa-pytest-result.json`。
- V5前端：`frontend`目录执行一次`npm run build`，`VITE_GAMEPLAY_VERSION=v5`、`CAMPUS_BACKEND_URL=http://127.0.0.1:8001`，exit0。Vite提示Phaser chunk超过500k。日志/摘要见`automated/qa-v5-build.log`、`automated/qa-v5-build-result.json`。
- 受影响旧测试输入：仅修改`tests/v5/test_generation_text_authority.py`的`content()`合成谜题名称，按真实effect及carrier产生门禁/普通终端或供电箱名称，非谜题名称、断言未改。只运行`test_eighteen_v2_contracts_preserve_structure_parameters_and_v1_history`与`test_role_text_reference_renaming_decoy_and_maximum_name`两族：exit0，20 passed、17 deselected、1条弃用warning。命令及日志见`automated/qa-legacy-input-tests-result.json`、`automated/qa-legacy-input-tests.log`。
- 浏览器：新增`tests/v5/run_passage_semantics_browser.mjs`，使用缓存的R1/R3 Synthetic draft+witness、全新专用TEMP SQLite、自有8002 Uvicorn fixture，网页仅从V5 dist和转发至8002加载。最终exit0，R1与R3各验证：出口初始disabled/“已锁定”且aria-describedby存在；真实鼠标点不发move；按缓存witness在首个move前完成门禁后按钮enabled/“可通行”；真实UI点击恰好一次move并抵达正确目的地（R1→EXIT，R3→G2）。总计11检查全过，外部请求0，服务已停止；6张截图及安全检查记录见`automated/qa-browser-result.json`。失败尝试与runner调整如实记录于`automated/qa-browser-attempt-history.json`，未改产品源码。

自动审批曾拒绝未设置SQLITE_PATH的纯测试命令，原因为潜在默认玩家DB回退；改用本轮TEMP专用SQLite路径后同一指定测试范围通过。未读取/写入玩家库。所有合成缓存仅在TEMP `campus-visual-sp-*`目录，不纳入仓库；真实模型/付费调用0。

## 限制与真人核验

浏览器仅验证Synthetic关卡1房与3房第一条向前通道；未完整通关3房，也未测存档、经典模式、手机或真实模型对名称规则的遵循。离线名称规则不证明任意中文复合词覆盖；画面/主题认可也不等于通行功能接受。自动截图不是人工验收。

请本人打开本阶段V5预览，生成一关并观察：门禁完成前出口显示“已锁定”且不能进入；门禁完成后显示“可通行”并抵达正确区域；储物柜仍只承担线索/物品用途。真人检查结果待本人提供。


纹理动态补载后续窄补及实际结果见[qa-texture-fix.md](qa-texture-fix.md)。本补验由Main先发现加载问题；首个不匹配主题包的Synthetic断言失败及后续主题化通过均保留。


针对Main发现的generic场景纹理问题，原主题化探索不替代generic复核；generic窄补的build/browser实际结果与失败保留记录见[qa-generic-texture-fix.md](qa-generic-texture-fix.md)。
