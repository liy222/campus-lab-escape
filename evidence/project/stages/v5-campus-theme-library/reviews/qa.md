# V5 校园主题素材库 QA

## 执行结果

本阶段按固定产物入口保存，不覆盖既有失败记录。产品构建一次；浏览器检查先后出现两次保留的非全绿执行，再完成定向续跑。Synthetic 浏览器样本只验证素材选择与呈现，不代表真实模型生成或关卡语义验收。

- 构建：在 `frontend` 执行 `npm run build`，环境为 `VITE_GAMEPLAY_VERSION=v5`、`CAMPUS_BACKEND_URL=http://127.0.0.1:8001`，退出码 0。日志：[qa-v5-build.log](../automated/qa-v5-build.log)，结构化结果：[qa-v5-build-result.json](../automated/qa-v5-build-result.json)。Vite 提示 Phaser chunk 超过 500 kB；构建仍成功。
- 首轮：`node tests/v5/run_theme_library_browser.mjs`，退出码 1。静态审计 68/68 记录通过：4 个包的 manifest、共享角色元数据、28 张原图的真实尺寸、alpha 像素与 bbox。图书馆包的 UI 主题匹配、三房背景/对象特写/终端两状态/重载检查通过。随后 Synthetic 任务很快 ready，但关卡列表未自动出现新卡片，25 秒等待超时。页面截图中当时列表只有此前样本。结果：[首轮目录](../automated/qa-2026-10-29T17-33-54-163Z-e6732213/)。
- 第一续跑：`node tests/v5/run_theme_library_browser.mjs --resume-from chemistry-lab`，退出码 1。化学实验室和计算机机房各完成三房背景、logbook/sealed-note 两种资料实际特写、终端 off/on、重载一致性；共 33 条检查记录通过。广播室请求被接受，但 UI 的“已就绪”定位器 45 秒未匹配。保留结果：[续跑目录](../automated/qa-2026-10-29T17-39-46-169Z-835c1375/)。随后只读查询该执行自建 TEMP 数据库的安全字段，三条 Synthetic job 均为 `ready`、`error_code=null`；失败是 UI 没有呈现当前新 job 的状态，不据此判定产品生成失败。
- 第二续跑：`node tests/v5/run_theme_library_browser.mjs --resume-from campus-broadcast`，退出码 0，18/18 记录通过。检查器按当前 job ID 轮询公开状态接口得到 `ready` 后，点击现有“刷新列表”进入广播室关卡；三房背景、资料与终端两状态、重载保持主题均通过。图集预览页面实际加载 28/28 张图片。结果：[广播室续跑目录](../automated/qa-2026-10-29T17-43-45-125Z-6b4384f8/)；图集截图：[theme-library-gallery.png](../automated/qa-2026-10-29T17-43-45-125Z-6b4384f8/theme-library-gallery.png)。
- 检查入口语法：`node --check tests/v5/run_theme_library_browser.mjs`，退出码 0。

## 范围和限制

所有浏览器运行使用独立 Synthetic fixture、临时账户、自建 TEMP 数据库及自有 8002 服务；结果记录外部请求 0、付费调用 0、真实模型调用 0、玩家数据库访问 false，服务均已停止。未完成整局通关、存档、经典模式或真人验收。第一轮与第一续跑的 exit 1 原样保留，不合并表述成单轮全绿；现有列表刷新边界只记录观察，不对产品列表自动刷新行为作通过结论。

美术效果入口：本地运行构建产物后打开 `/art-themes/campus-theme-library.html`，也可查看本阶段自动截图和每主题场景 PNG。真人尚未核验，等待本人查看。
