# 删除手机专项后的桌面窄验（2026-10-29）

独立AI QA：本次受影响桌面范围联合通过，无确认产品缺陷。未重跑原37项或完整路线，真人仍待核验。

## 清理范围

未发现需整文件删除的手机-only入口；删除混合脚本的手机viewport、触屏context、纯手机函数/调用/截图和touch-r3、feedback专用mode，保留桌面鼠标/键盘与规则、存档断言。涉及26个现行mjs：tests/e2e的run_ch01、run_m3、run_r1、run_play_ai_settings、run_upgrade及v31–v34、run_multiple_saves、run_visual_v40及fix/v41/v42、run_stage_ui、run_closeup_panel；tests/v5的run_browser、run_experience_browser、run_structure_variants_browser、run_visual_ui_browser；handpainted和panel-submit各run_browser/browser-body；save-delete/run_browser；以及明确临时转交的frontend/owner-evidence/v5-owner-smoke。另只改handpainted/prepare.py现行手机要求。新建窄验入口tests/v5/run_desktop_cleanup_browser.mjs。

26个修改后脚本node --check通过（247d3a）；Python准备文件内存compile通过。末次删除CLI模式与修正两处viewport_widths元数据后，对受影响脚本再次node --check通过（3d1b57、41d816）。未执行这些旧套件。review历史执行结论、seal/source list、原evidence/固定run/pin及release/archives均不改；旧源指纹属于旧epoch，不能声称仍等于本次修改后源码。线路orientation、非手机版touch状态/图片方向语义不作机械替换。

## 实际构建与集中检查

经典和V5分别使用VITE_GAMEPLAY_VERSION=upgrade/v5、CAMPUS_BACKEND_URL=http://127.0.0.1:8001，在frontend执行npm run build，各一次exit0（9f42fb/33b9b9，7.707秒/7.778秒）。[构建记录](../automated/desktop-cleanup-build1/result.json)。这是手机删除后的新源码epoch；先前手绘V5构建单独保留，不冒充本次构建。

|新控制器实际命令/退出|完成与保留范围|
|---|---|
|node tests/v5/run_desktop_cleanup_browser.mjs；e4b726/c435bc exit1|R1两桌面布局、真实Canvas热点及截图完成；API夹具同步后还等不存在的关闭控件超时。[原结果](../automated/desktop-smoke-2026-10-29T05-36-56-238Z-9c43fede/result.json)|
|同入口--remaining；023663/ff3656 exit1|确认同步已成功且App跨房自动关抽屉；最初“中心被挡”猜测不正确，改为仅现存继续游戏按钮可见时关闭。原件保留。|
|同入口--remaining；7a61c0/1155c6 exit1|两桌面线路实际旋转、CRT可见/输入及真实提交完成；QA无条件点击空草稿禁用clear，随后修为仅enabled时清。[记录](../automated/desktop-smoke-2026-10-29T05-40-11-594Z-ed9fcfb4/result.json)|
|同入口--r3-and-v5；8e0aa6/1e3a27 exit0|仅补R3实际设备点击/本地草稿与V5桌面特写、打开关闭存档面板；24记录/issues空。[末轮结果](../automated/desktop-smoke-2026-10-29T05-41-37-562Z-adadb34b/result.json)|

两尺寸均为1280×720、1920×1080。经典准备使用隔离公开API夹具，未把前置称为UI全路线；实际点击确认线路旋转、CRT提交、R3设备坐标可达。V5仅验证共享CSS受影响范围，存档面板可用控件至少44px且无横溢。经典/V5实际静态入口分别来自dist/dist-v5，结果记录有效入口指纹。R1/线路/CRT/R3/V5联合范围不求和成单轮，也不把3次QA适配失败改成成功；已成功范围和构建未重复。

截图在各轮目录，含经典R1/CRT/线路/面板以及末轮v5-desktop-1280/1920。Main以AI角色查看了R1、CRT和诊断图；不等于真人接受。原手绘37项首轮exit1及native-dialog焦点澄清保持原样，没有再通关。

所有服务/数据库为自有TEMP，8001浏览器请求只读本地静态产物或转发owned8002；没有读取或操作玩家8001、真实Key/账本/玩家库。自有服务已停，新增项目付费0；本次构建共2次，不额外构建。Synthetic技术结果不证明真实模型质量、物理设备或人类体验。交付时仍须明确邀请本人检查。SOURCE STOP。
