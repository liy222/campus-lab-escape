# 热点名称点击修复：独立 AI QA

当前结论：本次有限桌面范围联合通过，待用户本人体验核验；不是单轮全绿或真人验收。产品只调整 V5 active 样式，排除场景热点按钮，保留其居中 transform。

- 原问题证据来自 Main 开发诊断 `automated/hotspot-main-probe-2026-10-29T13-29-57-226Z/result.json`：旧版真实 CSS 的隔离 DOM 按住180ms，右移63.25px/下移23px，抬起未打开。这不是独立QA或实际API证据。
- 独立真实V5页面：owned TEMP/8002、合成主题与通用各1房；1280×720、1920×1080；名称文字左侧、标签左边缘、中心真实鼠标按住180ms。idle/hover/down及mouseup事件时最大位移均0px，抬起原点命中正确物件；每击恰好1次实际inspect并打开对应面板。两个场景/尺寸的Enter同样只inspect一次；存档抽屉打开时热点disabled，真实鼠标不触发inspect。
- 第一次inspect后的提示条令scene和热点同向下移50.5px；相对scene锚点0px，并非按压transform漂移。后续几何也为0。截图见下列实际运行目录。

## 实际执行与失败保留

1. `frontend: npm run build`，`VITE_GAMEPLAY_VERSION=v5`、`CAMPUS_BACKEND_URL=http://127.0.0.1:8001`；`7a0e95/f51c52` exit0，9.768s。仅构建一次：`automated/hotspot-pointer-build-20261029T133354Z/{result.json,output.txt}`。
2. `node tests/v5/run_hotspot_pointer_browser.mjs`：`6d5eda`/进程exit1，6记录。首按住0px已通过；QA把成功提示后的整场景移动误判为标签漂移，原结果保留于 `automated/hotspot-pointer-2026-10-29T13-34-48-723Z-a61e361d/`。
3. 同命令窄修坐标观察后，`21de3b/cdc780` exit1，40记录：主题两尺寸的全部指针/Enter/disabled通过；随后通用夹具误选旧主题卡。原结果 `automated/hotspot-pointer-2026-10-29T13-37-54-209Z-f6310b74/` 保留，复用其中主题实际记录。
4. `node tests/v5/run_hotspot_pointer_browser.mjs --generic-only`，`05ab79/7ec1fb` exit1：末清理route与context关闭竞态，无result；两张原截图及安全说明保留于 `automated/hotspot-pointer-2026-10-29T13-41-02-096Z-dfe120b2/`。异常曾将Synthetic临时Cookie带入本地工具记录；未复述或写入公开证据，完整headers/stdout不落盘，无玩家/真实凭据。保存完整异常日志的提案被自动安全审查拒绝，改为只输出安全字段，未执行该日志写入。
5. 仅修QA清理并精确选新标题，仍`--generic-only`，`07b1b4/7b2c18` exit0，40记录/issues[]：`automated/hotspot-pointer-2026-10-29T13-44-39-998Z-54351fac/`。其中两张generic截图可视。未重建或重测主题。

新控制器：`tests/v5/run_hotspot_pointer_browser.mjs`；准备/窄修 `node --check` 均exit0。两个最终适用结果均绑定同一dist-v5 index SHA并正常停止自有服务。控制器有上述QA修正epoch，产品/构建未重复变化。上述记录不相加冒充一个完整套件。

## 限制与核验入口

仅Synthetic定向输入检查，未测新模型质量、全路线、经典版或旧37项；项目付费0，没有请求玩家8001或操作玩家库。截图由自动化生成，独立QA是AI智能体。请用户打开当前V5预览，分别在名称文字左侧和边缘按住再松开，确认稳定打开；真人接受尚未发生。
