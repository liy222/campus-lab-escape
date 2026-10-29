# 手绘重建桌面独立QA（2026-10-29）

独立AI QA：本次有限桌面范围通过；首轮退出码1保留，不能称单次全绿。真人尚未核验。

|实际操作|命令及结果|
|---|---|
|唯一构建|frontend中 `npm run build`，VITE_GAMEPLAY_VERSION=v5、CAMPUS_BACKEND_URL=http://127.0.0.1:8001；015e2f/5ae884 exit0，64模块，10.008秒，既有Phaser大块警告；[构建记录](../automated/build-20261029-run1/result.json)|
|集中浏览器|`node tests/v5/run_handpainted_rebuild_browser.mjs`；7b2dd2/2e6d76 exit1，37项中36通过、1项过严焦点断言，控制器异常0；[原结果](../automated/browser-2026-10-29T05-06-00-985Z-3c2b8e97/result.json)|
|最小焦点诊断|同入口 `--focus-only`；7b3562/6893e8 exit0，仅2项诊断。新TEMP、一房Synthetic确认框夹具，无通关或整轮重跑；[诊断记录](../automated/focus-2026-10-29T05-10-21-657Z-92dc7467/result.json)|

四项旧失败均通过：通用钥匙场景/特写使用同一黄铜钥匙身份，无保险丝错配；通用结算中性，不虚构观测资料归档；删除存档后Tab/ShiftTab仍在V5面板，Escape正常关闭；按当前实际src动态模拟404，确有拦截并回退到可用图。全部两候选失败时保留名称/说明和可读文字，每个HTML候选仅失败一次，稳定等待期间无新增请求。场景与特写共用URL时没有要求它们必须发出不同请求。

仅桌面1280×720及1920×1080：可用控件实际最小44px、被测正文最小14px，无横溢。实际加载状态、特写与完成态可见。三主题背景、第二/第三房两线路和顺序通过真实UI提交，三房hard Synthetic到服务器EXIT；同一路线另做一次保存→发现资料→选择恢复，主题/背景/变体保持，线索回到早期状态。

实际响应记录含15张handpainted-v2手绘PNG的来源/字节哈希，所用PNG尺寸与manifest一致；同一物件场景/特写共用高分源。透明物件与bbox处理来源见Main的output/art-concepts/rainy-astronomy/handpainted-v2/assets.json（alpha阈值16）；本次QA核实际贴图、尺寸及截图，不另宣称独立完成逐像素alpha边界审计。源码、构建入口、manifest及所用图指纹均在原结果。QA实际查看[第一房](../automated/browser-2026-10-29T05-06-00-985Z-3c2b8e97/theme-G1.png)、[第三房](../automated/browser-2026-10-29T05-06-00-985Z-3c2b8e97/theme-G3.png)和[通用钥匙](../automated/browser-2026-10-29T05-06-00-985Z-3c2b8e97/generic-key.png)，未见本轮可见阻断；画风与主题接受仍由本人判断。

原焦点失败澄清：ShiftTab后activeElement=BODY、document.hasFocus=false，但dialog.open与:modal仍true，是页面外/浏览器chrome焦点；后续键盘仅到取消/确认或同样失焦，没有背景应用控件获焦。取消后回当前存档面板。原inside_dialog断言过严，不是已证明的产品缺陷；未改产品。加入诊断只变了这一个新controller的源码epoch，两份实际记录各保留当时指纹，构建/产品/manifest未再改变。诊断原件的inputs数组沿用了整轮模板，不能当作重跑两关：该run实际只创建上述一房焦点夹具，以scope、命令和诊断代码为准；原件不改写。

项目付费0，实际build1；owned8002均停止，无玩家8001/真实Key/账本/玩家库操作。未跑旧36/旧10/后端套件或手机检查；Synthetic路线不证明真实模型语义、真人难度或整体接受。旧失败与OPEN不自动改写；大阶段交付后须明确邀请本人核验。SOURCE STOP。
